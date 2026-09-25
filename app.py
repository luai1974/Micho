
import os, csv, io
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app=Flask(__name__)
app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY") or "dev-only-change-me"
db_url=os.environ.get("DATABASE_URL","sqlite:///salary_v2.db")
if db_url.startswith("postgres://"): db_url="postgresql://"+db_url[len("postgres://"):]
app.config["SQLALCHEMY_DATABASE_URI"]=db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
app.config["SESSION_COOKIE_HTTPONLY"]=True
app.config["SESSION_COOKIE_SAMESITE"]="Lax"
app.config["SESSION_COOKIE_SECURE"]=os.environ.get("FLASK_ENV")=="production"
app.permanent_session_lifetime=timedelta(hours=8)
db=SQLAlchemy(app); csrf=CSRFProtect(app)
from jinja2 import DictLoader

EMBEDDED_TEMPLATES = {'admin.html': '{% extends "base.html" %}{% block content %}<div class="actions"><a class="btn" href="{{url_for(\'employee_new\')}}">+ עובד חדש</a><form><input type="month" name="month" value="{{month}}" onchange="this.form.submit()"></form></div><div class="card"><h2>עובדים — {{month}}</h2><table><tr><th>עובד</th><th>שעות</th><th>לפני מפרעות</th><th>מפרעות</th><th>לתשלום</th><th>פעולות</th></tr>{% for e,h,g,a,n in rows %}<tr><td>{{e.name}}</td><td>{{"%.2f"|format(h)}}</td><td>₪{{"%.2f"|format(g)}}</td><td>₪{{"%.2f"|format(a)}}</td><td><b>₪{{"%.2f"|format(n)}}</b></td><td><div class="actions"><a class="btn" href="{{url_for(\'employee_detail\',eid=e.id,month=month)}}">כרטיס</a><a class="btn secondary" href="{{url_for(\'employee_edit\',eid=e.id)}}">עריכה</a><form method="post" action="{{url_for(\'employee_delete\',eid=e.id)}}" onsubmit="return confirm(\'למחוק?\')"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><button class="danger">מחיקה</button></form></div></td></tr>{% endfor %}</table></div>{% endblock %}', 'detail.html': '{% extends "base.html" %}{% block content %}{% set e,w,a,h,g,ad,n=data %}<div class="actions"><a class="btn secondary" href="{{url_for(\'dashboard\',month=month)}}">חזרה</a><form><input type="month" name="month" value="{{month}}" onchange="this.form.submit()"></form><a class="btn" href="{{url_for(\'export_csv\',eid=e.id,month=month)}}">ייצוא CSV</a></div><h1>{{e.name}}</h1><div class="grid"><div class="stat">שעות<div class="big">{{"%.2f"|format(h)}}</div></div><div class="stat">תעריף<div class="big">₪{{"%.2f"|format(e.hourly_rate)}}</div></div><div class="stat">לפני מפרעות<div class="big">₪{{"%.2f"|format(g)}}</div></div><div class="stat">מפרעות<div class="big">₪{{"%.2f"|format(ad)}}</div></div><div class="stat">לתשלום<div class="big">₪{{"%.2f"|format(n)}}</div></div></div>\n<div class="grid"><div class="card"><h3>הוספת שעות</h3><form method="post" action="{{url_for(\'add_work\',eid=e.id)}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><input type="date" name="date" required><input type="number" step=".25" min="0" name="hours" placeholder="שעות" required><input name="note" placeholder="הערה"><button>הוסף</button></form></div><div class="card"><h3>הוספת מפרעה</h3><form method="post" action="{{url_for(\'add_advance\',eid=e.id)}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><input type="date" name="date" required><input type="number" step=".01" min="0" name="amount" placeholder="סכום ₪" required><input name="note" placeholder="הערה"><button>הוסף</button></form></div></div>\n<div class="card"><h3>שעות עבודה</h3><table><tr><th>תאריך</th><th>שעות</th><th>הערה</th><th></th></tr>{% for x in w %}<tr><td>{{x.work_date}}</td><td>{{x.hours}}</td><td>{{x.note}}</td><td><form method="post" action="{{url_for(\'delete_work\',wid=x.id)}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><button class="danger">מחק</button></form></td></tr>{% endfor %}</table></div><div class="card"><h3>מפרעות</h3><table><tr><th>תאריך</th><th>סכום</th><th>הערה</th><th></th></tr>{% for x in a %}<tr><td>{{x.advance_date}}</td><td>₪{{"%.2f"|format(x.amount)}}</td><td>{{x.note}}</td><td><form method="post" action="{{url_for(\'delete_advance\',aid=x.id)}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><button class="danger">מחק</button></form></td></tr>{% endfor %}</table></div>{% endblock %}', 'base.html': '<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ניהול עובדים ושכר</title>\n<style>*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f4f6f8;color:#182230}.top{background:#142238;color:white;padding:15px 5%;display:flex;justify-content:space-between;align-items:center}.wrap{max-width:1100px;margin:25px auto;padding:0 16px}.card,.stat{background:white;border-radius:14px;padding:20px;margin:12px 0;box-shadow:0 2px 12px #00000010}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.big{font-size:23px;font-weight:bold;margin-top:8px}.btn,button{border:0;border-radius:9px;padding:10px 14px;background:#142238;color:white;text-decoration:none;cursor:pointer}.secondary{background:#667085}.danger{background:#a93226}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}input{width:100%;padding:11px;margin:5px 0 12px;border:1px solid #ccd3db;border-radius:8px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #e8eaed;text-align:right}.login{max-width:420px;margin:10vh auto}.flash{padding:12px;background:#fdecec;border-radius:8px}.muted{color:#667085}</style></head><body>\n{% if session.uid %}<div class="top"><b>ניהול עובדים ושכר</b><div>{{session.name}} <form style="display:inline" method="post" action="{{url_for(\'logout\')}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><button class="secondary">יציאה</button></form></div></div>{% endif %}\n<div class="wrap">{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{% block content %}{% endblock %}</div></body></html>', 'employee.html': '{% extends "base.html" %}{% block content %}{% set e,w,a,h,g,ad,n=data %}<form><input type="month" name="month" value="{{month}}" onchange="this.form.submit()"></form><h1>שלום {{e.name}}</h1><div class="grid"><div class="stat">שעות<div class="big">{{"%.2f"|format(h)}}</div></div><div class="stat">תעריף<div class="big">₪{{"%.2f"|format(e.hourly_rate)}}</div></div><div class="stat">שכר לפני מפרעות<div class="big">₪{{"%.2f"|format(g)}}</div></div><div class="stat">מפרעות<div class="big">₪{{"%.2f"|format(ad)}}</div></div><div class="stat">יתרה לתשלום<div class="big">₪{{"%.2f"|format(n)}}</div></div></div><div class="card"><h3>פירוט שעות</h3><table><tr><th>תאריך</th><th>שעות</th><th>הערה</th></tr>{% for x in w %}<tr><td>{{x.work_date}}</td><td>{{x.hours}}</td><td>{{x.note}}</td></tr>{% endfor %}</table></div><div class="card"><h3>פירוט מפרעות</h3><table><tr><th>תאריך</th><th>סכום</th><th>הערה</th></tr>{% for x in a %}<tr><td>{{x.advance_date}}</td><td>₪{{"%.2f"|format(x.amount)}}</td><td>{{x.note}}</td></tr>{% endfor %}</table></div>{% endblock %}', 'employee_form.html': '{% extends "base.html" %}{% block content %}<div class="card"><h2>{{"עריכת עובד" if emp else "עובד חדש"}}</h2><form method="post"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><label>שם מלא</label><input name="name" value="{{emp.name if emp else \'\'}}" required><label>טלפון</label><input name="phone" value="{{emp.phone if emp else \'\'}}"><label>שם משתמש</label><input name="username" value="{{emp.username if emp else \'\'}}" required><label>{{"סיסמה חדשה — ריק = ללא שינוי" if emp else "סיסמה"}}</label><input type="password" name="password" {{"" if emp else "required"}}><label>תעריף לשעה ₪</label><input type="number" step=".01" min="0" name="hourly_rate" value="{{emp.hourly_rate if emp else \'\'}}" required>{% if emp %}<label><input style="width:auto" type="checkbox" name="active" {% if emp.active %}checked{% endif %}> חשבון פעיל</label><br><br>{% endif %}<button>שמירה</button> <a class="btn secondary" href="{{url_for(\'dashboard\')}}">ביטול</a></form></div>{% endblock %}', 'login.html': '{% extends "base.html" %}{% block content %}<div class="card login"><h1>כניסה למערכת</h1><form method="post"><input type="hidden" name="csrf_token" value="{{csrf_token()}}"><label>שם משתמש</label><input name="username" required autocomplete="username"><label>סיסמה</label><input type="password" name="password" required autocomplete="current-password"><button style="width:100%">כניסה</button></form></div>{% endblock %}'}

app.jinja_loader = DictLoader(EMBEDDED_TEMPLATES)

class Admin(db.Model):
    id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(80),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)

class Employee(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(160),nullable=False); phone=db.Column(db.String(40))
    username=db.Column(db.String(80),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False)
    hourly_rate=db.Column(db.Float,nullable=False,default=0); active=db.Column(db.Boolean,default=True,nullable=False)
    work_entries=db.relationship("WorkEntry",cascade="all, delete-orphan",backref="employee")
    advances=db.relationship("Advance",cascade="all, delete-orphan",backref="employee")

class WorkEntry(db.Model):
    id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employee.id"),nullable=False)
    work_date=db.Column(db.Date,nullable=False); hours=db.Column(db.Float,nullable=False); note=db.Column(db.String(300))

class Advance(db.Model):
    id=db.Column(db.Integer,primary_key=True); employee_id=db.Column(db.Integer,db.ForeignKey("employee.id"),nullable=False)
    advance_date=db.Column(db.Date,nullable=False); amount=db.Column(db.Float,nullable=False); note=db.Column(db.String(300))

def init_db():
    db.create_all()
    admin_user=os.environ.get("ADMIN_USERNAME","admin")
    admin_pass=os.environ.get("ADMIN_PASSWORD")
    if admin_pass and not Admin.query.filter_by(username=admin_user).first():
        db.session.add(Admin(username=admin_user,password_hash=generate_password_hash(admin_pass)))
        db.session.commit()

with app.app_context(): init_db()

def required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrap(*a,**kw):
            if not session.get("uid"): return redirect(url_for("login"))
            if role and session.get("role")!=role: abort(403)
            return fn(*a,**kw)
        return wrap
    return deco

def month_bounds(month):
    try: start=datetime.strptime(month,"%Y-%m").date()
    except: start=datetime.now().replace(day=1).date(); month=start.strftime("%Y-%m")
    if start.month==12: end=start.replace(year=start.year+1,month=1)
    else: end=start.replace(month=start.month+1)
    return month,start,end

def calc(eid,month):
    month,start,end=month_bounds(month)
    e=db.session.get(Employee,eid)
    works=WorkEntry.query.filter(WorkEntry.employee_id==eid,WorkEntry.work_date>=start,WorkEntry.work_date<end).order_by(WorkEntry.work_date).all()
    advs=Advance.query.filter(Advance.employee_id==eid,Advance.advance_date>=start,Advance.advance_date<end).order_by(Advance.advance_date).all()
    hours=sum(x.hours for x in works); adv=sum(x.amount for x in advs); gross=hours*e.hourly_rate
    return e,works,advs,hours,gross,adv,gross-adv

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["username"].strip(); p=request.form["password"]
        a=Admin.query.filter_by(username=u).first()
        if a and check_password_hash(a.password_hash,p):
            session.clear(); session.permanent=True; session.update(uid=a.id,role="admin",name="מנהל")
            return redirect(url_for("dashboard"))
        e=Employee.query.filter_by(username=u,active=True).first()
        if e and check_password_hash(e.password_hash,p):
            session.clear(); session.permanent=True; session.update(uid=e.id,role="employee",name=e.name)
            return redirect(url_for("dashboard"))
        flash("שם משתמש או סיסמה שגויים")
    return render_template("login.html")

@app.post("/logout")
@required()
def logout(): session.clear(); return redirect(url_for("login"))

@app.get("/health")
def health(): return {"status":"ok"},200

@app.get("/dashboard")
@required()
def dashboard():
    month=request.args.get("month",datetime.now().strftime("%Y-%m"))
    if session["role"]=="employee": return render_template("employee.html",month=month,data=calc(session["uid"],month))
    rows=[(e,*calc(e.id,month)[3:]) for e in Employee.query.order_by(Employee.name).all()]
    return render_template("admin.html",month=month,rows=rows)

@app.route("/employee/new",methods=["GET","POST"])
@required("admin")
def employee_new():
    if request.method=="POST":
        if Employee.query.filter_by(username=request.form["username"].strip()).first():
            flash("שם המשתמש כבר קיים"); return render_template("employee_form.html",emp=None)
        e=Employee(name=request.form["name"].strip(),phone=request.form.get("phone","").strip(),
          username=request.form["username"].strip(),password_hash=generate_password_hash(request.form["password"]),
          hourly_rate=float(request.form["hourly_rate"]),active=True)
        db.session.add(e); db.session.commit(); return redirect(url_for("dashboard"))
    return render_template("employee_form.html",emp=None)

@app.route("/employee/<int:eid>/edit",methods=["GET","POST"])
@required("admin")
def employee_edit(eid):
    e=db.get_or_404(Employee,eid)
    if request.method=="POST":
        other=Employee.query.filter(Employee.username==request.form["username"].strip(),Employee.id!=eid).first()
        if other: flash("שם המשתמש כבר קיים"); return render_template("employee_form.html",emp=e)
        e.name=request.form["name"].strip(); e.phone=request.form.get("phone","").strip()
        e.username=request.form["username"].strip(); e.hourly_rate=float(request.form["hourly_rate"]); e.active="active" in request.form
        if request.form.get("password"): e.password_hash=generate_password_hash(request.form["password"])
        db.session.commit(); return redirect(url_for("dashboard"))
    return render_template("employee_form.html",emp=e)

@app.post("/employee/<int:eid>/delete")
@required("admin")
def employee_delete(eid):
    e=db.get_or_404(Employee,eid); db.session.delete(e); db.session.commit(); return redirect(url_for("dashboard"))

@app.get("/employee/<int:eid>")
@required("admin")
def employee_detail(eid):
    month=request.args.get("month",datetime.now().strftime("%Y-%m")); return render_template("detail.html",month=month,data=calc(eid,month))

@app.post("/employee/<int:eid>/work")
@required("admin")
def add_work(eid):
    db.get_or_404(Employee,eid); d=datetime.strptime(request.form["date"],"%Y-%m-%d").date()
    db.session.add(WorkEntry(employee_id=eid,work_date=d,hours=float(request.form["hours"]),note=request.form.get("note","").strip()))
    db.session.commit(); return redirect(url_for("employee_detail",eid=eid,month=d.strftime("%Y-%m")))

@app.post("/work/<int:wid>/delete")
@required("admin")
def delete_work(wid):
    x=db.get_or_404(WorkEntry,wid); eid=x.employee_id; m=x.work_date.strftime("%Y-%m")
    db.session.delete(x); db.session.commit(); return redirect(url_for("employee_detail",eid=eid,month=m))

@app.post("/employee/<int:eid>/advance")
@required("admin")
def add_advance(eid):
    db.get_or_404(Employee,eid); d=datetime.strptime(request.form["date"],"%Y-%m-%d").date()
    db.session.add(Advance(employee_id=eid,advance_date=d,amount=float(request.form["amount"]),note=request.form.get("note","").strip()))
    db.session.commit(); return redirect(url_for("employee_detail",eid=eid,month=d.strftime("%Y-%m")))

@app.post("/advance/<int:aid>/delete")
@required("admin")
def delete_advance(aid):
    x=db.get_or_404(Advance,aid); eid=x.employee_id; m=x.advance_date.strftime("%Y-%m")
    db.session.delete(x); db.session.commit(); return redirect(url_for("employee_detail",eid=eid,month=m))

@app.get("/export/<int:eid>/<month>")
@required("admin")
def export_csv(eid,month):
    e,w,a,h,g,ad,n=calc(eid,month); s=io.StringIO(); out=csv.writer(s)
    out.writerow(["עובד",e.name]); out.writerow(["חודש",month]); out.writerow([])
    out.writerow(["תאריך","שעות","הערה"])
    for x in w: out.writerow([x.work_date,x.hours,x.note])
    out.writerow([]); out.writerow(["סה״כ שעות",h]); out.writerow(["תעריף",e.hourly_rate]); out.writerow(["לפני מפרעות",g]); out.writerow(["מפרעות",ad]); out.writerow(["לתשלום",n])
    b=io.BytesIO(("\ufeff"+s.getvalue()).encode("utf-8")); b.seek(0)
    return send_file(b,as_attachment=True,download_name=f"salary_{eid}_{month}.csv",mimetype="text/csv")

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
