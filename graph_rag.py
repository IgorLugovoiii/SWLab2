"""
graph_rag.py - ГРАФ ЗНАНЬ І GraphRAG (п. 4):
  1. граф networkx з фактів (вузли - сутності, ребра - зв'язки) і малюнок graph.png;
  2. виявлення спільнот (python-louvain);
  3. коротке резюме кожної спільноти через LLM;
  4. map-reduce: фінальна відповідь з резюме спільнот;
  5. для порівняння - vector-RAG: топ-N чанків напряму в LLM.
Відповіді записуються у output/graphrag_answers.txt.
"""
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import community as community_louvain  # noqa: E402  (пакет python-louvain)

from config import OUT, TOP_N, GLOBAL_QUESTIONS, SIMPLE_QUESTIONS
from llm import generate_text
from search import vector_search

TYPE_COLORS = {"Person": "#4C78A8", "Machine": "#F58518", "Organization": "#54A24B", "Place": "#E45756"}


def build_graph(facts: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    for f in facts:
        s, o = f["subject"].lower(), f["object"].lower()
        G.add_node(s, label=f["subject"], kind=f["subject_type"])
        G.add_node(o, label=f["object"], kind=f["object_type"])
        if G.has_edge(s, o):
            G[s][o]["relations"].append(f["relation"])
            G[s][o]["weight"] += 1
        else:
            G.add_edge(s, o, relations=[f["relation"]], weight=1)
    with open(os.path.join(OUT, "graph_nodes.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "type"])
        for n, d in G.nodes(data=True):
            w.writerow([d["label"], d["kind"]])
    with open(os.path.join(OUT, "graph_edges.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "target", "relations"])
        for s, o, d in G.edges(data=True):
            w.writerow([G.nodes[s]["label"], G.nodes[o]["label"], ";".join(d["relations"])])
    print(f"[5] Граф: вузлів {G.number_of_nodes()}, ребер {G.number_of_edges()}. Файли: output/graph_nodes.csv, graph_edges.csv")
    return G


def draw(G: nx.DiGraph, partition: dict) -> None:
    pos = nx.spring_layout(G, seed=7, k=1.2, iterations=200)
    plt.figure(figsize=(16, 12))
    for kind, color in TYPE_COLORS.items():
        nodes = [n for n in G.nodes if G.nodes[n]["kind"] == kind]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=color, node_size=500, alpha=0.9, label=kind)
    nx.draw_networkx_edges(G, pos, edge_color="#AAAAAA", arrows=True, arrowsize=10, width=0.8)
    nx.draw_networkx_labels(G, pos, labels={n: G.nodes[n]["label"] for n in G.nodes}, font_size=6)
    plt.title("Граф знань: сутності та зв'язки з корпусу", fontsize=14)
    plt.legend(loc="upper left", fontsize=9)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "graph.png"), dpi=150)
    plt.close()
    print("[5b] Картинку збережено: output/graph.png")


def communities(G: nx.DiGraph) -> dict:
    U = G.to_undirected()
    partition = community_louvain.best_partition(U, weight="weight", random_state=42)
    groups = defaultdict(list)
    for node, cid in partition.items():
        groups[cid].append(node)
    print(f"[6] Спільнот (Louvain): {len(groups)}")
    return {"partition": partition, "groups": groups}


def _community_text(G: nx.DiGraph, members: list[str]) -> str:
    lines = []
    for s, o, d in G.edges(data=True):
        if s in members and o in members:
            lines.append(f"- {G.nodes[s]['label']} --{', '.join(d['relations'])}--> {G.nodes[o]['label']}")
    names = ", ".join(G.nodes[m]["label"] for m in members)
    return f"Entities: {names}\nRelations:\n" + "\n".join(lines[:80])


def summarize_communities(G: nx.DiGraph, groups: dict) -> dict[int, str]:
    summaries = {}
    for cid, members in groups.items():
        if len(members) < 3:  # дрібніші спільноти не резюмуємо, щоб не витрачати ліміт
            continue
        prompt = ("Below are entities and relations extracted from documents about the history of computing. "
                  "Write a short summary (3-5 sentences, in Ukrainian) of what this group of entities is about "
                  "and how they are connected. Use only the information below.\n\n" + _community_text(G, members))
        summaries[cid] = generate_text(prompt).strip()
        print(f"  резюме спільноти {cid}: {len(members)} сутностей")
    return summaries


def graph_rag_answer(question: str, summaries: dict[int, str]) -> str:
    joined = "\n\n".join(f"Community {cid}:\n{s}" for cid, s in summaries.items())
    prompt = ("You answer a question using summaries of communities from a knowledge graph. "
              "Synthesize across the summaries, answer in Ukrainian, and say which communities support the answer.\n\n"
              f"SUMMARIES:\n{joined}\n\nQUESTION: {question}")
    return generate_text(prompt).strip()


def vector_rag_answer(question: str, chunks: list[dict], vecs) -> tuple[str, list[dict]]:
    top = vector_search(question, chunks, vecs, k=TOP_N)
    context = "\n\n".join(f"[{c['chunk_id']} | {c['title']}]\n{c['text']}" for c, _ in top)
    prompt = ("Answer the question using only the context below. Answer in Ukrainian.\n\n"
              f"CONTEXT:\n{context}\n\nQUESTION: {question}")
    return generate_text(prompt).strip(), [c for c, _ in top]


def run(facts: list[dict], chunks: list[dict], vecs) -> None:
    G = build_graph(facts)
    comm = communities(G)
    draw(G, comm["partition"])
    summaries = summarize_communities(G, comm["groups"])

    lines = ["ПРОСТІ ПИТАННЯ (векторний пошук: найрелевантніший фрагмент)", ""]
    # Прості питання: відповідь = найрелевантніший фрагмент тексту (без виклику LLM, економимо ліміт)
    for q in SIMPLE_QUESTIONS:
        top = vector_search(q, chunks, vecs, k=1)
        best, score = top[0]
        lines += [f"Питання: {q}", f"Найрелевантніший фрагмент ({best['chunk_id']}, схожість {score:.2f}):",
                  best["text"][:600] + " ...", ""]
        print(f"Q: {q}\nA (фрагмент {best['chunk_id']}): {best['text'][:200]} ...\n")

    lines += ["ГЛОБАЛЬНІ ПИТАННЯ: GraphRAG проти vector-RAG", ""]
    for q in GLOBAL_QUESTIONS:
        g_ans = graph_rag_answer(q, summaries)
        v_ans, used = vector_rag_answer(q, chunks, vecs)
        lines += [
            f"Питання: {q}",
            "GraphRAG (резюме спільнот -> фінальна відповідь):",
            g_ans,
            "",
            f"vector-RAG (топ-{TOP_N} чанків -> відповідь), чанки: {', '.join(c['chunk_id'] for c in used)}:",
            v_ans,
            "",
        ]
        print(f"GLOBAL: {q}\n-- GraphRAG: {g_ans}\n-- vector-RAG: {v_ans}\n")

    lines += ["РЕЗЮМЕ СПІЛЬНОТ", ""]
    for cid, s in summaries.items():
        names = ", ".join(G.nodes[m]["label"] for m in comm["groups"][cid])
        lines += [f"Спільнота {cid}: {names}", s, ""]
    with open(os.path.join(OUT, "graphrag_answers.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[7] Відповіді записано у output/graphrag_answers.txt")
