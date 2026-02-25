from flask import Flask, render_template, redirect, url_for, request, flash, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime, timedelta
import csv
import io

from config import Config
from models import db, User, Calculation

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        if User.query.filter_by(email=email).first():
            flash("Email já cadastrado.")
            return redirect(url_for("register"))

        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()

        flash("Conta criada com sucesso!")
        return redirect(url_for("login"))

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Login inválido.")

    return render_template("login.html")


# ================= LOGOUT =================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ================= DASHBOARD =================

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    result = None

    # ===== CALCULO =====
    if request.method == "POST":
        odds = request.form.getlist("odds")
        odds = [float(o) for o in odds if o]

        investment = float(request.form.get("investment"))

        inverse_sum = sum((1 / o) for o in odds)

        if inverse_sum < 1:
            stakes = [(investment / (o * inverse_sum)) for o in odds]
            profit = round((stakes[0] * odds[0]) - investment, 2)

            result = {
                "surebet": True,
                "roi": round((1 - inverse_sum) * 100, 2),
                "stakes": [round(s, 2) for s in stakes],
                "profit": profit
            }

            calc = Calculation(
                user_id=current_user.id,
                odds=",".join(f"{o:.2f}" for o in odds),
                investment=investment,
                roi=result["roi"],
                profit=profit
            )
            db.session.add(calc)
            db.session.commit()
        else:
            result = {"surebet": False}

    # ===== FILTRO =====
    period = request.args.get("period", "7d")
    query = Calculation.query.filter_by(user_id=current_user.id)

    now = datetime.utcnow()
    if period == "7d":
        query = query.filter(Calculation.created_at >= now - timedelta(days=7))
    elif period == "30d":
        query = query.filter(Calculation.created_at >= now - timedelta(days=30))

    history = query.order_by(Calculation.created_at.desc()).all()

    # ===== METRICAS =====
    totals = query.with_entities(
        func.count(Calculation.id),
        func.coalesce(func.sum(Calculation.investment), 0.0),
        func.coalesce(func.sum(Calculation.profit), 0.0),
        func.coalesce(func.avg(Calculation.roi), 0.0),
    ).first()

    metrics = {
        "count": int(totals[0] or 0),
        "total_investment": float(totals[1] or 0.0),
        "total_profit": float(totals[2] or 0.0),
        "avg_roi": float(totals[3] or 0.0),
    }

    return render_template("dashboard.html",
                           result=result,
                           history=history,
                           metrics=metrics,
                           period=period)


# ================= EXPORT CSV =================

@app.route("/history/export")
@login_required
def export_history():
    query = Calculation.query.filter_by(user_id=current_user.id)\
        .order_by(Calculation.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "odds", "investment", "roi", "profit", "created_at"])

    for r in query:
        writer.writerow([r.id, r.odds, r.investment, r.roi, r.profit, r.created_at])

    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=historico.csv"})


# ================= LIMPAR HISTORICO =================

@app.route("/history/clear", methods=["POST"])
@login_required
def clear_history():
    Calculation.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Histórico limpo com sucesso.")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)