from flask import Blueprint, render_template, redirect

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def home():
    return render_template('index.html', active_page='home')

@views_bp.route('/about')
def about():
    return render_template('about.html', active_page='about')

@views_bp.route('/predictor')
@views_bp.route('/tool')
def tool():
    return redirect('/upload')

@views_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard')

@views_bp.route('/recommend')
def recommend():
    return render_template('recommend.html', active_page='recommend')

@views_bp.route('/explainability')
def explainability():
    return render_template('explainability.html', active_page='explainability')

@views_bp.route('/analytics')
def analytics():
    return render_template('analytics.html', active_page='analytics')

@views_bp.route('/history')
def history():
    return redirect('/dashboard')

@views_bp.route('/upload')
def upload():
    return render_template('upload.html', active_page='upload')

@views_bp.route('/admin')
def admin():
    return render_template('admin.html', active_page='admin')

@views_bp.route('/login')
def login():
    return render_template('login.html', active_page='login')

@views_bp.route('/register')
def register():
    return render_template('register.html', active_page='register')
