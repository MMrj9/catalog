from flask import Flask, render_template, request, flash
from flask import redirect, jsonify, url_for, session, make_response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Product, User
import random
import string
import datetime
import os
import json
from flask.ext.login import LoginManager, login_required, login_user, \
    logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session
from requests.exceptions import HTTPError


class Auth:
    CLIENT_ID = '298861287864-91nm0i50ld'\
                'aifmokoqgjngmc9o4snchb.apps.googleusercontent.com'
    CLIENT_SECRET = 'QLl86MJLerXnyQo2fhXJFlMx'
    REDIRECT_URI = 'http://localhost:5000/gCallback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email']

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = "udacity"
app.name = "Catalog"

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
db = DBSession()


@login_manager.user_loader
def load_user(user_id):
    return db.query(User).get(int(user_id))


def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth


@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect("/")
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    return render_template('login.html', auth_url=auth_url)


@app.route('/gCallback')
def callback():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        google = get_google_auth(state=session['oauth_state'])
        try:
            request.url = request.url.replace("http", "https")
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except HTTPError:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                user = User()
                user.email = email
            user.name = user_data['name']
            user.tokens = json.dumps(token)
            db.add(user)
            db.commit()
            login_user(user)
            return redirect("/")
        return 'Could not fetch your information.'


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/')
@app.route('/category/')
def showCategories():
    categories = db.query(Category).all()
    return render_template('categories.html', categories=categories)


@app.route('/category/new/', methods=['GET', 'POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'], created_date=datetime.datetime.now())
        db.add(newCategory)
        db.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
@login_required
def editCategory(category_id):
    editedCategory = db.query(
        Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            return redirect(url_for('showCategories'))
    else:
        return render_template(
            'editCategory.html', category=editedCategory)


@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_id):
    categoryToDelete = db.query(
        Category).filter_by(id=category_id).one()

    if request.method == 'POST':
        productsToDelete = db.query(
            Product).filter_by(category_id=categoryToDelete.id).all()

        for p in productsToDelete:
            db.delete(p)

        db.delete(categoryToDelete)
        db.commit()
        return redirect(
            url_for('showCategories', category_id=category_id))
    else:
        return render_template(
            'deleteCategory.html', category=categoryToDelete)


@app.route('/category/<int:category_id>/products/JSON')
def showProductsJSON(category_id):
    category = db.query(Category).filter_by(id=category_id).one()
    products = db.query(Product).filter_by(
        category_id=category_id).all()
    return jsonify(Products=[p.serialize for p in products])


@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/products/')
def showProducts(category_id):
    category = db.query(Category).filter_by(id=category_id).one()
    products = db.query(Product).filter_by(
        category_id=category_id).all()
    return render_template(
        'products.html', products=products, category=category)


@app.route(
    '/category/<int:category_id>/product/new/', methods=['GET', 'POST'])
@login_required
def newProduct(category_id):
    if request.method == 'POST':
        newProduct = Product(
            name=request.form['name'], description=request.form['description'],
            price=request.form['price'],
            category_id=category_id, created_date=datetime.datetime.now(),
            created_by_id=current_user.id)
        db.add(newProduct)
        db.commit()

        return redirect(url_for('showProducts', category_id=category_id))
    else:
        return render_template('newProduct.html', category_id=category_id)

    return render_template('newProduct.html', category=category)


@app.route('/category/<int:category_id>/product/<int:product_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editProduct(category_id, product_id):
    editedProduct = db.query(Product).filter_by(id=product_id).one()
    if current_user.get_id == editedProduct.created_by_id:
        if request.method == 'POST':
            if request.form['name']:
                editedProduct.name = request.form['name']
            if request.form['description']:
                editedProduct.description = request.form['description']
            if request.form['price']:
                editedProduct.price = request.form['price']
            db.add(editedProduct)
            db.commit()
            return redirect(url_for('showProducts', category_id=category_id))
        else:
            return render_template(
                'editProduct.html', category_id=category_id,
                product_id=product_id, product=editedProduct)
    else:
        flash("This user can't edit this product")


@app.route('/category/<int:category_id>/product/<int:product_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteProduct(category_id, product_id):
    productToDelete = db.query(Product).filter_by(id=product_id).one()
    if current_user.get_id == editedProduct.created_by_id:
        if request.method == 'POST':
            db.delete(productToDelete)
            db.commit()
            return redirect(url_for('showProducts', category_id=category_id))
        else:
            return render_template(
                'deleteProduct.html', product=productToDelete)
    else:
        flash("This user can't delete this product")


@app.route('/category/<int:category_id>/products/<int:product_id>')
def showProduct(category_id, product_id):
    product = db.query(Product).filter_by(id=product_id).one()
    return
    render_template(
            'showProduct.html', category_id=category_id, product=product)


def main():
    app.debug = True
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
