from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import GraphEdge, GraphNode
from app.services.graph import graph_payload, get_or_create_node, ensure_edge
from app.utils import admin_required

bp = Blueprint("graph", __name__, url_prefix="/graph")


@bp.route("/")
@login_required
def view():
    return render_template("graph/view.html")


@bp.route("/data")
@login_required
def data():
    return jsonify(graph_payload())


@bp.route("/manage", methods=["GET", "POST"])
@login_required
@admin_required
def manage():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_node":
            name = request.form.get("name", "").strip()
            node_type = request.form.get("node_type", "concept")
            desc = request.form.get("description", "").strip()
            if name:
                get_or_create_node(name, node_type, desc)
                db.session.commit()
                flash("节点已添加", "success")
        elif action == "add_edge":
            s_name = request.form.get("source_name", "").strip()
            t_name = request.form.get("target_name", "").strip()
            relation = request.form.get("relation", "关联").strip() or "关联"
            if s_name and t_name:
                s = get_or_create_node(s_name, "concept")
                t = get_or_create_node(t_name, "concept")
                ensure_edge(s, t, relation)
                db.session.commit()
                flash("关系已添加", "success")
        return redirect(url_for("graph.manage"))
    nodes = GraphNode.query.order_by(GraphNode.id.desc()).limit(50).all()
    edges = GraphEdge.query.order_by(GraphEdge.id.desc()).limit(50).all()
    return render_template("graph/manage.html", nodes=nodes, edges=edges)
