"""简易知识图谱：根据文档元数据与标签自动/半自动建图。"""
from __future__ import annotations

from app.extensions import db
from app.models import Document, GraphEdge, GraphNode
from app.services.rag import extract_keywords


def get_or_create_node(name: str, node_type: str, description: str = "", document_id=None) -> GraphNode:
    node = GraphNode.query.filter_by(name=name).first()
    if node:
        if description and not node.description:
            node.description = description
        if document_id and not node.document_id:
            node.document_id = document_id
        return node
    node = GraphNode(
        name=name,
        node_type=node_type,
        description=description or "",
        document_id=document_id,
    )
    db.session.add(node)
    db.session.flush()
    return node


def ensure_edge(source: GraphNode, target: GraphNode, relation: str) -> None:
    exists = GraphEdge.query.filter_by(
        source_id=source.id, target_id=target.id, relation=relation
    ).first()
    if exists:
        return
    db.session.add(GraphEdge(source_id=source.id, target_id=target.id, relation=relation))


def sync_document_graph(doc: Document) -> None:
    """为单篇文档同步节点与关系。"""
    doc_node = get_or_create_node(
        name=f"文档:{doc.title}",
        node_type="document",
        description=doc.summary or doc.title,
        document_id=doc.id,
    )
    dept_node = get_or_create_node(doc.department, "department", f"{doc.department}相关部门")
    ensure_edge(doc_node, dept_node, "属于")

    if doc.category:
        cat_node = get_or_create_node(doc.category.name, "concept", doc.category.description or "")
        ensure_edge(doc_node, cat_node, "分类为")

    tag_text = doc.tags or ""
    tags = [t.strip() for t in tag_text.split(",") if t.strip()]
    if not tags:
        tags = extract_keywords(doc.content, top_k=5).split(",")
        tags = [t for t in tags if t]
        if tags:
            doc.tags = ",".join(tags)

    for tag in tags[:8]:
        kw_node = get_or_create_node(tag, "keyword", f"关键词：{tag}")
        ensure_edge(doc_node, kw_node, "含有")

    db.session.commit()


def graph_payload() -> dict:
    nodes = GraphNode.query.all()
    edges = GraphEdge.query.all()
    type_color = {
        "document": "#2563eb",
        "department": "#059669",
        "project": "#d97706",
        "keyword": "#7c3aed",
        "concept": "#dc2626",
    }
    return {
        "nodes": [
            {
                "id": n.id,
                "name": n.name,
                "category": n.node_type,
                "symbolSize": 42 if n.node_type == "document" else 28,
                "itemStyle": {"color": type_color.get(n.node_type, "#64748b")},
                "document_id": n.document_id,
            }
            for n in nodes
        ],
        "links": [
            {
                "source": e.source_id,
                "target": e.target_id,
                "relation": e.relation,
            }
            for e in edges
        ],
        "categories": [
            {"name": "document"},
            {"name": "department"},
            {"name": "project"},
            {"name": "keyword"},
            {"name": "concept"},
        ],
    }
