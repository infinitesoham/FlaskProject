from flask import Flask,flash, render_template, request, redirect, url_for,session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps


from flask import send_file
from werkzeug.utils import secure_filename
from io import BytesIO

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import IntegerField


import plotly.express as px
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.sqlite3"

db = SQLAlchemy(app)

from datetime import datetime
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler


def authrequired(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return func(*args,**kwargs)
    return inner

def adminrequired(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        user=User.query.get(session['user'])
        if not user.user_name=='admin':
            return redirect(url_for('login'))
        return func(*args,**kwargs)
    return inner



class UploadForm(FlaskForm):
    book_id = IntegerField('Book ID')
    pdf_file = FileField('PDF File', validators=[FileRequired()])


class PdfFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('Books.book_id'))
    filename = db.Column(db.String(255))
    data = db.Column(db.LargeBinary)

class User(db.Model):
    __tablename__='User'
    user_id = db.Column(db.Integer, primary_key = True)
    user_name = db.Column(db.String,unique=True, nullable = False)
    user_email = db.Column(db.String, nullable = False)
    user_password = db.Column(db.String, nullable = False)
    admin=db.Column(db.String, nullable = False)

class Books(db.Model):
    __tablename__='Books'
    book_id = db.Column(db.Integer, primary_key = True)
    book_name = db.Column(db.String, nullable = False)
    book_author = db.Column(db.String, nullable = True)
    book_content = db.Column(db.Text,nullable=True)
    book_available_from=db.Column(db.DateTime,default=datetime.utcnow)
    book_category_id = db.Column(db.Integer,db.ForeignKey('Category.category_id'), primary_key = False)

    pdf=db.relationship('PdfFile',backref='Book',lazy=True)

class Category(db.Model):
    __tablename__='Category'
    category_id = db.Column(db.Integer, primary_key = True)
    category_name = db.Column(db.String, nullable = False)
    category_date=db.Column(db.DateTime,default=datetime.utcnow)

    books=db.relationship('Books',backref='category',lazy=True)

class Orders(db.Model):
    __tablename__='Orders'
    order_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, primary_key = False)
    book_id = db.Column(db.Integer, primary_key = False)
    Order_status = db.Column(db.String, nullable = False)
    Order_date=db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
    pr=User.query.filter_by(user_name='admin').first()
    if not pr:
        admin=User(user_id=1,user_name='admin',user_email='email@gmail.com',user_password='admin',admin=True)
        db.session.add(admin)
        db.session.commit()

def revokebook():
    with app.app_context():
        current_time=datetime.utcnow()
        orders=Orders.query.all()

        for order in orders:
            if (current_time-order.Order_date)>timedelta(days=5) and order.Order_status=='Approved':
                db.session.delete(order)

        db.session.commit()









@app.route('/')
def landing_page(): 
    return render_template('index.html')



@app.route('/login')
def login(): 
    return render_template('login.html')

@app.route('/login',methods=['Post'])
def loginpost(): 
    username=request.form.get('username')
    password=request.form.get('password')
    user=User.query.filter_by(user_name=username,admin=False).first()
    if not user:
        flash('Please give valid user credential')
        return redirect(url_for('login'))
    if not user.user_password==password:
        flash('Please put correct password')
        return redirect(url_for('login'))
    session['user']=user.user_id
    return redirect(url_for('dashboard'))

@app.route('/adminlogin')
def adminlogin():
    return render_template('adminlogin.html')


@app.route('/adminlogin',methods=['Post'])
def adminloginpost():
    username=request.form.get('username')
    password=request.form.get('password')
    user=User.query.filter_by(user_name=username,admin=True).first()
    if not user:
        flash('Please give valid admin login credential','success')
        return redirect(url_for('adminlogin'))
    if not user.user_password==password:
        flash('Please give correct password to login')
        return redirect(url_for('adminlogin'))
    session['user']=user.user_id
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('user_id',None)
    return render_template('index.html') 





@app.route('/register')

def register():
    return render_template('register.html')

@app.route('/register',methods=['Post'])
def registerpost():
    username=request.form.get('username')
    password=request.form.get('password')
    email=request.form.get('email')
    usercheck=User.query.filter_by(user_name=username).first()
    if usercheck:
        flash('Username already taken')
        return redirect(url_for('register'))
    user=User(user_name=username,user_email=email,user_password=password,admin=False)
    db.session.add(user)
    db.session.commit()
    return render_template('index.html')




@app.route('/dashboard')
@authrequired
def dashboard(): 
    books=Books.query.order_by(Books.book_available_from).all()
    return render_template('dashboard.html',user=User.query.get(session['user']),search='simple',books=books)

@app.route('/dashboard',methods=['post'])
@authrequired
def search():
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        selected_category = request.form.get('category')
    if selected_category=='category1':
        categories=Category.query.filter_by(category_name=search_query).all()
        return render_template('dashboard.html',user=User.query.get(session['user']),categories=categories,search='customized')
    elif selected_category=='category2':
        categories=Category.query.all()
        return render_template('dashboard.html',user=User.query.get(session['user']),query=search_query,categories=categories,search='customized')
    else:
        categories=Category.query.all()
        return render_template('dashboard.html',user=User.query.get(session['user']),author=search_query,categories=categories,search='customized')


@app.route('/mybook/<int:userid>/<int:bookid>')
@authrequired
def addmybook(userid,bookid):
    userid=userid
    bookid=bookid
    ordercheck=Orders.query.filter_by(user_id=userid,book_id=bookid).first()
    number=Orders.query.filter_by(user_id=userid).count()
    if ordercheck and ordercheck.Order_status=='Pending':
        flash('Already book requested','success')
        return redirect(url_for('dashboard'))
    if ordercheck and ordercheck.Order_status=='Approved':
        flash('Already book issued','success')
        return redirect(url_for('dashboard'))
    if number==5:
        flash('User have reached maximum book request limit','success')
        return redirect(url_for('dashboard'))
    order=Orders(user_id=userid,book_id=bookid,Order_status='Pending')
    db.session.add(order)
    db.session.commit() 
    ordersapproved=Orders.query.filter_by(Order_status='Approved',user_id=User.query.get(session['user']).user_id).all()
    orders=Orders.query.filter_by(Order_status='Pending',user_id=User.query.get(session['user']).user_id).all()
    return redirect(url_for('mybook'))

@app.route('/mybookuser')
@authrequired
def mybook():
    ordersapproved=Orders.query.filter_by(Order_status='Approved',user_id=User.query.get(session['user']).user_id)
    orders=Orders.query.filter_by(Order_status='Pending',user_id=User.query.get(session['user']).user_id)
    books=Books.query.all()
    time=timedelta(days=5)
    date=datetime.utcnow()
    return render_template('mybook.html',orders=orders,ordersapproved=ordersapproved,books=books,time=time,date=date)


@app.route('/admin')
@adminrequired
def admin(): 
    return render_template('admin.html',user=User.query.get(session['user']))

@app.route('/categories')
@adminrequired
def categories(): 
    categories=Category.query.all()
    return render_template('categories.html',categories=categories)

@app.route('/books')
@adminrequired
def books(): 
    books=Books.query.all()
    return render_template('books.html',books=books)

@app.route('/addcategory')
@adminrequired
def addcategory(): 
    return render_template('addcategory.html')

@app.route('/addcategory',methods=['Post'])
@adminrequired
def categoryadd():
    category=request.form.get('categoryname')
    categorycheck=Category.query.filter_by(category_name=category).first()
    if categorycheck:
        flash('Category already added','success')
        return redirect(url_for('addcategory'))
    categoryadd=Category(category_name=category)
    db.session.add(categoryadd)
    db.session.commit()
    return render_template('admin.html',user=User.query.get(session['user']))































@app.route('/editcategory/<int:categoryid>')
@adminrequired
def categoryedit(categoryid):
    categoryid=categoryid
    return render_template('categoryedit.html',categoryid=categoryid)



@app.route('/editcategory/<int:categoryid>',methods=['Post'])
@adminrequired
def categoryeditupdate(categoryid):
    categoryid=categoryid
    categoryname=request.form.get('Categoryname')
    category=Category.query.filter_by(category_id=categoryid).first()
    category.category_name=categoryname
    db.session.commit()
    return redirect(url_for('categories'))



@app.route('/editbook/<int:bookid>')
@adminrequired
def editbook(bookid):
    bookid=bookid
    categories=Category.query.all()
    return render_template('editbook.html',bookid=bookid,categories=categories)

@app.route('/editbook/<int:bookid>',methods=['Post'])
@adminrequired
def editbookupdate(bookid):
    bookid=bookid
    bookname=request.form.get('Bookname')
    bookcategory=request.form.get('Bookcategory')
    bookauthor=request.form.get('bookauthor')
    bookcontent=request.form.get('bookcontent')
    book=Books.query.get(bookid)
    Categories=Category.query.all()
    book.book_name=bookname
    book.book_category_id=Category.query.filter_by(category_name=bookcategory).first().category_id
    book.book_author=bookauthor
    book.book_content=bookcontent
    db.session.commit()
    flash('Book updated succesfully','success')
    return redirect(url_for('books'))

@app.route('/addbook')
@adminrequired
def addbook():
    categories=Category.query.all() 
    return render_template('addbook.html',categories=categories)

@app.route('/addbook',methods=['Post'])
@adminrequired
def bookadd():
    bookname=request.form.get('bookname')
    bookcategory=request.form.get('bookcategory')
    bookauthor=request.form.get('bookauthor')
    bookreadable=request.form.get('bookreadable')

    bookcategoryget=Category.query.filter_by(category_name=bookcategory).first()
    bookcategoryidget=bookcategoryget.category_id
    bookcheck=Books.query.filter_by(book_name=bookname,book_author=bookauthor).first()
    if bookcheck:
        flash('Book already added','success')
        return redirect(url_for('addbook'))
    check=Books.query.filter_by().first()
    if not check:
        book=Books(book_id=100,book_name=bookname,book_author=bookauthor,book_content=bookreadable,book_category_id=bookcategoryidget)
    else:
        id=Books.query.order_by(Books.book_id.desc()).first().book_id
        book=Books(book_id=id+1,book_name=bookname,book_author=bookauthor,book_content=bookreadable,book_category_id=bookcategoryidget)
    db.session.add(book)
    db.session.commit()
    return render_template('admin.html',user=User.query.get(session['user']))


@app.route('/orders')
@adminrequired
def orders():
    orders=Orders.query.all()
    users=User.query.all()
    books=Books.query.all()
    return render_template('orders.html',orders=orders,users=users,books=books)

@app.route('/approvestatus/<int:orderid>')
@adminrequired
def approvestatus(orderid):
    orderid=orderid
    order=Orders.query.filter_by(order_id=orderid).first()
    order.Order_date=datetime.utcnow()
    order.Order_status='Approved'
    db.session.commit()
    return render_template('admin.html',user=User.query.get(session['user']))

@app.route('/bookread/<int:bookid>')
@authrequired
def bookread(bookid):
    bookid=bookid
    book=Books.query.filter_by(book_id=bookid).first()
    show=book.book_content
    pdffile=PdfFile.query.filter_by(book_id=bookid).first()
    return render_template('bookcontent.html',show=show,books=books,pdf=pdffile)

@app.route('/bookdrop/<int:orderid>')
@authrequired
def bookdrop(orderid):
    orderid=orderid
    order=Orders.query.get(orderid)
    db.session.delete(order)
    db.session.commit()
    orders=Orders.query.filter_by(Order_status='Pending',user_id=User.query.get(session['user']).user_id)
    ordersapproved=Orders.query.filter_by(Order_status='Approved',user_id=User.query.get(session['user']).user_id)
    return redirect(url_for('mybook',orders=orders,ordersapproved=ordersapproved))












@app.route('/categorydrop/<int:categoryid>')
@adminrequired
def categorydrop(categoryid):
    categoryid=categoryid
    category=Category.query.get(categoryid)
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('categories'))

@app.route('/bookdropadmin/<int:bookid>')
@adminrequired
def bookadmindrop(bookid):
    bookid=bookid
    book=Books.query.get(bookid)
    db.session.delete(book)
    db.session.commit()
    orders=Orders.query.filter_by(book_id=bookid).all()
    for order in orders:
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('books'))


@app.route('/showuser/<int:userid>')
@adminrequired
def showuser(userid):
    userid=userid
    user=User.query.get(userid)
    orders=Orders.query.all()
    books=Books.query.all()
    booksuser=Orders.query.filter_by(user_id=userid,Order_status='Approved')
    return render_template('showuser.html',user=user,orders=orders,booksuser=booksuser,books=books)





















@app.route('/upload', methods=['GET', 'POST'])
@adminrequired
def upload_file():
    form = UploadForm()

    if form.validate_on_submit():
        book_id = form.book_id.data
        pdf_file = form.pdf_file.data
        filename = secure_filename(pdf_file.filename)
        data = pdf_file.read()

        new_pdf = PdfFile(book_id=book_id, filename=filename, data=data)
        db.session.add(new_pdf)
        db.session.commit()

        flash('File uploaded succesfully','Success')
        return redirect(url_for('bookpdf'))
    books=Books.query.all()
    return render_template('upload.html', form=form,books=books)


@app.route('/download/<int:pdf_id>')
def download_file(pdf_id):
    pdf_file = PdfFile.query.get_or_404(pdf_id)
    return send_file(BytesIO(pdf_file.data), as_attachment=True, download_name=pdf_file.filename)

@app.route('/bookpdf')
def bookpdf():
    books=Books.query.all()
    pdf_files=PdfFile.query.all()
    return render_template('bookpdfs.html',books=books,pdf_files=pdf_files)









@app.route('/analyzewindow')
@adminrequired
def windowshow():
    return render_template('analyse.html')


@app.route('/analyze')
@adminrequired
def analize():
    # Books=Orders.query.all()
    booksee={}
    books=Books.query.all()
    for book in books:
        booksee[book.book_name]=Orders.query.filter_by(book_id=book.book_id).count()
    names = list(booksee.keys())
    values = list(booksee.values())
    fig = px.pie(names=names, values=values, title='Pie Chart')
    chart_div = fig.to_html(full_html=False)

    return render_template('visual.html', chart_div=chart_div)

@app.route('/categoryanalysis')
@adminrequired
def categoryanalyse():
    categoriees=Books.query.all()
    categorydive={}
    namecat=Category.query.all()
    for category in categoriees:
        for name in namecat:
            if category.book_category_id==name.category_id:  
                categorydive[name.category_name]=Books.query.filter_by(book_category_id=category.book_category_id).count()
    for name in namecat:
        if name.category_name not in categorydive.keys():
            categorydive[name.category_name]=0
    names=list(categorydive.keys())
    values=list(categorydive.values())
    plt.plot(names, values)
    plt.xlabel('Category Name')
    plt.ylabel('Books in that Category')
    plt.title('Category distribution')
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_data = base64.b64encode(img.getvalue()).decode()

    plt.clf()
    
    return render_template('categoryvisual.html',plot_data=plot_data,data=categorydive)










scheduler = BackgroundScheduler()
scheduler.add_job(revokebook,'interval',seconds=10)
scheduler.start()