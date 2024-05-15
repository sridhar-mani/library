from flask import Flask,render_template, request, redirect, url_for, flash, session, make_response
from app import app
from models import db,User,Section,Book,BookRequest,Mybook,UserFeedback
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import date,timedelta
from weasyprint import HTML
import os
import uuid
import pathlib

#login and registration

@app.route('/',methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/login',methods=['POST'])
def login_post():
    username=request.form.get('username')
    password=request.form.get('password')

    if not username or not password:
        flash('Please fill out all fields')
        return redirect(url_for('register'))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Username not exist')
        return redirect(url_for('login'))

    if not check_password_hash(user.passhash, password):
        flash('Incorrect password')
        return redirect(url_for('login'))
        
    session['user_id']=user.id
    flash('Login successful')
        
    return redirect(url_for('library'))


@app.route('/register',methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/register',methods=['POST'])
def register_post():
    username=request.form.get('username')
    password=request.form.get('password')
    confirm_password=request.form.get('confirm_password')
    name=request.form.get('name')
    profilepic=request.files.get('profilepic')
    
    if not username or not password or not confirm_password:
        flash('Please fill out all fields')
        return redirect(url_for('register'))
    
    if password is confirm_password:
        flash('Passwords do not match')
        return redirect(url_for('register'))

    user = User.query.filter_by(username=username).first()

    if user:
        flash('Username already exist')
        return redirect(url_for('register'))
    
    password_hash=generate_password_hash(password)
    
    allowed_formats={'png','tiff','jpg','jpeg'}
    
    if profilepic:
        filename=secure_filename(profilepic.filename)
        if ('.' in filename and filename.rsplit('.',1)[1].lower() in allowed_formats):
            unique_filename=str(uuid.uuid4())+os.path.splitext(filename)[1]
            profile_final_post=os.path.join(app.config['UPLOAD_FOLDER_PPIC'],unique_filename)
            os.makedirs(app.config['UPLOAD_FOLDER_PPIC'])
            profilepic.save(profile_final_post)    
            new_user = User(username=username,passhash=password_hash,name=name,profile_pic=profile_final_post)
        else:
            flash('Invalid file format.Please use PNG or Tiff.')
            return redirect(url_for('register'))
    else:
        new_user = User(username=username,passhash=password_hash,name=name)
    
    db.session.add(new_user)
    db.session.commit()
    flash('Registration successful')
    return redirect(url_for('login'))

#seperate auth for admin and user is made

def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login')
            return redirect(url_for('login'))
    return inner

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login')
            return redirect(url_for('login'))
        user=User.query.get(session['user_id'])
        if not user.is_admin:
            flash('Please login as administrator')
            return redirect(url_for('library'))
        return func(*args, **kwargs)
    return inner

@app.route('/profile',methods=['GET'])
@auth_required
def profile():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    return render_template('profile.html',user=user,librarian=librarian)

@app.route('/profile',methods=['POST'])
@auth_required
def profile_post():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    username=request.form.get('username')
    password=request.form.get('npassword')
    cpassword=request.form.get('cpassword')
    name=request.form.get('name')
    profilepic=request.files.get('profilepic')
    
    
    if not username or not password or not cpassword:
        flash('Please fill out all fields')
        return render_template('profile.html',user=user,librarian=librarian)
    
    user=User.query.get(session['user_id'])

    if not check_password_hash(user.passhash,cpassword):
        flash('Incorrect password')
        return render_template('profile.html',user=user,librarian=librarian)

    if username==user.username:    
        new_username = User.query.filter_by(username=username).first()
        if new_username:
            flash('Username already exists')
            return render_template('profile.html',user=user,librarian=librarian)
    if password == cpassword:
        flash('New password should not be same as current password')
        return render_template('profile.html',user=user,librarian=librarian)

    password_hash=generate_password_hash(password)

    allowed_formats={'png','tiff','jpg','jpeg'}
    
    if profilepic:
        if user.profile_pic:
            if os.path.exists(user.profile_pic):
                os.remove(user.profile_pic)
        filename=secure_filename(profilepic.filename)
        if ('.' in filename and filename.rsplit('.',1)[1].lower() in allowed_formats):
            unique_filename=str(uuid.uuid4())+os.path.splitext(filename)[1]
            profile_final_post=os.path.join(app.config['UPLOAD_FOLDER_PPIC'],unique_filename)
            profilepic.save(profile_final_post)
    else:
        profile_final_post=user.profile_pic

    user.username=username
    user.passhash=password_hash
    user.name=name
    user.profile_pic=profile_final_post

    db.session.commit()
    flash('Changes successful')
    return redirect(url_for('profile'))

@app.route('/logout',methods=['GET'])
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    sections=Section.query.all()
    return render_template('admin.html',librarian=librarian,sections=sections)

@app.route('/section/add')
@admin_required
def add_section():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    return render_template('section/add.html',librarian=librarian)

@app.route('/section/add', methods=['POST'])
@admin_required
def add_section_post():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    name=request.form.get('name')
    today=date.today()
    description=request.form.get('description')
    if not name:
        flash('Please fill out all fields')
        return redirect(url_for('add_section',librarian=librarian))
    section = Section(name=name,date_created=today,description=description)
    db.session.add(section)
    db.session.commit()
    flash('Section added successfully')
    return redirect(url_for('admin',librarian=librarian))

@app.route('/section/<int:id>/')
@admin_required
def show_section(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    section=Section.query.get(id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    requests=BookRequest.query.all()
    mybook=Mybook.query.all()
    my_books=[book.book_id for book in mybook]
    requested_books = [request.book_id for request in requests]
    return render_template('section/show.html',section=section,mybooks=my_books,user=user,requested_books=requested_books,librarian=librarian)

@app.route('/section/<int:id>/edit')
@admin_required
def edit_section(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    section=Section.query.get(id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    return render_template('section/edit.html',librarian=librarian,section=section)

@app.route('/section/<int:id>/edit', methods=['POST'])
@admin_required
def edit_section_post(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    section=Section.query.get(id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    name=request.form.get('name')
    description=request.form.get('description')
    if not name or not description:
        flash('Please fill out all fields')
        return redirect(url_for('edit_section',librarian=librarian))
    section.name=name
    section.description=description
    db.session.commit()
    flash('Section details updated successfully')
    return redirect(url_for('admin',librarian=librarian))


@app.route('/section/<int:id>/delete')
@admin_required
def delete_section(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    section=Section.query.get(id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    return render_template('section/delete.html',section=section,librarian=librarian)

@app.route('/section/<int:id>/delete', methods=['POST'])
@admin_required
def delete_section_post(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    section=Section.query.get(id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    remainin=Section.query.filter(Section.id!=id).all()
    db.session.delete(section)
    db.session.commit()
    for i,s in enumerate(remainin,start=1):
        s.id=i
    db.session.commit()
    flash('Section deleted')
    return redirect(url_for('admin',librarian=librarian))

@app.route('/admin/performance')
@admin_required
def performance():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    sections=Section.query.all()
    books=Book.query.all()
    section_name=[section.name for section in sections]
    book_nos=[len(section.books) for section in sections]
    book_names=[book.bname for book in books]
    requests=[book.request_counts for book in books]
    return render_template('performance.html',librarian=librarian,section_name=section_name,book_nos=book_nos,book_names=book_names,requests=requests)

#after this the books routes start

@app.route('/book/add/<int:section_id>')
@admin_required
def add_book(section_id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    sections=Section.query.all()
    section=Section.query.get(section_id)
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    return render_template('book/add.html',librarian=librarian,section=section, sections=sections)

@app.route('/book/add/', methods=['POST'])
@admin_required
def add_book_post():
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    bname=request.form.get('bname')
    content=request.form.get('content')
    author_name=request.form.get('author')
    price=request.form.get('price')
    vol_no=request.form.get('volume')
    pages=request.form.get('pages')
    section_id=request.form.get('section_id')
    cover=request.files.get('cover')

    section=Section.query.get(section_id)

    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin',librarian=librarian))
    
    if not bname or not content or not author_name or not pages or not section_id or not price:
        flash('Please fill all details')
        return redirect(url_for('add_book',librarian=librarian,section_id=section_id))

    try:
        price=float(price)
        if vol_no:
            vol_no=int(vol_no)
        pages=int(pages)

    except ValueError:
        flash('Please fill all details')
        return redirect(url_for('add_book',librarian=librarian,section_id=section_id))

    if price<=0 or pages<=0:
        flash('Invalid details')
        return redirect(url_for('add_book',librarian=librarian,section_id=section_id))
    
    allowed_formats={'png','tiff'}
    
    if cover:
        filename=secure_filename(cover.filename)
        if ('.' in filename and filename.rsplit('.',1)[1].lower() in allowed_formats):
            unique_filename=str(uuid.uuid4())+os.path.splitext(filename)[1]
            cover_final=os.path.join(app.config['UPLOAD_FOLDER_BCOVER'],unique_filename)
            os.makedirs(app.config['UPLOAD_FOLDER_BCOVER'])
            cover.save(cover_final)
            new_book=Book(bname=bname,price=price,author_name=author_name,content=content,volume_no=vol_no,section_id=section_id,pages=pages,cover=cover_final)
        else:
            flash('Invalid file format.Please use PNG or Tiff.')
            return redirect(url_for('add_book',librarian=librarian,section_id=section_id))
    else:
        new_book=Book(bname=bname,price=price,author_name=author_name,content=content,volume_no=vol_no,section_id=section_id,pages=pages)
    
    db.session.add(new_book)
    db.session.commit()
    flash('Book added successfully')
    return redirect(url_for('show_section',librarian=librarian, id=section_id))

@app.route('/book/<int:id>/edit')
@admin_required
def edit_book(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin

    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('show_section',librarian=librarian, section=section))
    section = Section.query.get(book.section_id)
    if not section:
        flash('Section for the book does not exist')
        return redirect(url_for('show_sections',librarian=librarian))
    sections = Section.query.all()
    return render_template('book/edit.html', book=book,librarian=librarian, section=section, sections=sections)

@app.route('/book/<int:id>/edit', methods=['POST'])
@admin_required
def edit_book_post(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin

    bname=request.form.get('bname')
    content=request.form.get('content')
    author_name=request.form.get('author')
    price=request.form.get('price')
    vol_no=request.form.get('volume')
    pages=request.form.get('pages')
    section_id=request.form.get('section_id')
    cover=request.files.get('cover')

    book=Book.query.get(id)

    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    
    if not bname or not content or not author_name or not pages or not section_id or not price:
        flash('Please fill all details')
        return redirect(url_for('add_book',section_id=section_id,librarian=librarian))

    try:
        price=float(price)
        if vol_no:
            vol_no=int(vol_no)
        pages=int(pages)

    except ValueError:
        flash('Please fill all details')
        return redirect(url_for('add_book',section_id=section_id,librarian=librarian))

    if price<=0 or pages<=0:
        flash('Invalid details')
        return redirect(url_for('add_book',section_id=section_id,librarian=librarian))
    
    allowed_formats={'png','tiff'}
     
    if cover:
        if os.path.exists(book.cover):
            os.remove(book.cover)
        filename=secure_filename(cover.filename)
        if ('.' in filename and filename.rsplit('.',1)[1].lower() in allowed_formats):
            unique_filename=str(uuid.uuid4())+os.path.splitext(filename)[1]
            cover_final=os.path.join(app.config['UPLOAD_FOLDER_BCOVER'],unique_filename)
            cover.save(cover_final)

        else:
            flash('Invalid file format.Please use PNG or Tiff.')
            return redirect(url_for('edit_book',librarian=librarian,section_id=section_id))
    else:
        cover_final=book.cover
    
    book.cover=cover_final
    book.bname=bname
    book.content=content
    book.author_name=author_name
    book.price=price
    book.vol_no=vol_no
    book.pages=pages
    book.section_id=section_id
    db.session.commit()

    flash('Book details updated successfully')
    return redirect(url_for('show_section', id=section_id,librarian=librarian))

@app.route('/book/<int:id>/delete',methods=['POST'])
@admin_required
def delete_book_post(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin

    book=Book.query.get(id)

    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    section_id = book.section_id
    remainin=Book.query.filter(Book.id!=id).all()
    db.session.delete(book)
    db.session.commit()
    for i,s in enumerate(remainin,start=1):
        s.id=i
    db.session.commit()
    flash('Book deleted')
    return redirect(url_for('show_section', id=section_id,librarian=librarian))

@app.route('/book/<int:id>/delete')
@admin_required
def delete_book(id):
    user=User.query.get(session['user_id'])
    librarian=user.is_admin
    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin'))
    return render_template('book/delete.html',librarian=librarian,user=user,book=book)

@app.route('/book/<int:id>/access_request')
@admin_required
def access_request(id):
    use=User.query.get(session['user_id'])
    librarian=use.is_admin
    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    request=BookRequest.query.filter_by(book_id=id).first()
    if not request:
        flash('Request does not exist')
        return redirect(url_for('admin',librarian=librarian))
    user=User.query.get(request.user_id)
    if not user:
        flash('User does not exist')
        return redirect(url_for('admin',librarian=librarian))
    return render_template('book/access_request.html',librarian=librarian,book=book,request=request,user=user)

@app.route('/book/<int:id>/access_request/issue')
@admin_required
def access_request_issue(id):
    use=User.query.get(session['user_id'])
    librarian=use.is_admin

    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    request=BookRequest.query.filter_by(book_id=id).first()
    if not request:
        flash('Request does not exist')
        return redirect(url_for('admin',librarian=librarian))
    user=User.query.get(request.user_id)
    if not user:
        flash('User does not exist')
        return redirect(url_for('admin',librarian=librarian))
    today=date.today()
    return_date = today + timedelta(days=7)
    addbook= Mybook(user_id=user.id, book_id=id, issue_date=today, return_date=return_date)
    
    book.issue_date = today
    book.return_date = return_date
    book.user_id=user.id
    
    request.is_approved=True
    
    db.session.add(addbook)
    
    db.session.commit()
    
    return redirect(url_for('show_section',librarian=librarian,id=book.section_id))

@app.route('/book/<int:id>/access_request/reject')
@admin_required
def access_request_reject(id):
    use=User.query.get(session['user_id'])
    librarian=use.is_admin

    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    request=BookRequest.query.filter_by(book_id=id).first()
    if not request:
        flash('Request does not exist')
        return redirect(url_for('admin',librarian=librarian))
    user=User.query.get(request.user_id)
    if not user:
        flash('User does not exist')
        return redirect(url_for('admin',librarian=librarian))
    
    db.session.delete(request)
    
    db.session.commit()
    
    return render_template('book/access_request.html',librarian=librarian,book=book,request=request,user=user)

@app.route('/book/<int:id>/revoke_access')
@admin_required
def revoke_access(id):
    use=User.query.get(session['user_id'])
    librarian=use.is_admin

    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    request=BookRequest.query.filter_by(book_id=id).first()
    if not request:
        flash('Request does not exist')
        return redirect(url_for('admin',librarian=librarian))
    user=User.query.get(request.user_id)
    if not user:
        flash('User does not exist')
        return redirect(url_for('admin',librarian=librarian))
    return render_template('book/revoke_access.html',librarian=librarian,book=book,request=request,user=user)

@app.route('/book/<int:id>/revoke_access/done',methods=['POST'])
@admin_required
def revoke_access_post(id):
    use=User.query.get(session['user_id'])
    librarian=use.is_admin

    book=Book.query.get(id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('admin',librarian=librarian))
    request=BookRequest.query.filter_by(book_id=id).first()
    if not request:
        flash('Request does not exist')
        return redirect(url_for('admin',librarian=librarian))
    user=User.query.get(request.user_id)
    if not user:
        flash('User does not exist')
        return redirect(url_for('admin',librarian=librarian))
    
    addbook = Mybook.query.filter_by(book_id=id).first()
    
    db.session.delete(addbook)
    
    book.issue_date = None
    book.return_date = None
    book.user_id = None
    
    db.session.delete(request)
    
    db.session.commit()
    
    return redirect(url_for('show_section',librarian=librarian,id=book.section_id))

#---------- user routes --------------

@app.route('/library')
@auth_required
def library():
    user=User.query.get(session['user_id'])
    
    if user.is_admin:
        return redirect(url_for('admin'))
    
    requests=BookRequest.query.all()
    requested_books = [request.book_id for request in requests]
    myrequested_books = [request.book_id for request in requests if request.user_id == user.id]
    
    parameter=request.args.get('parameter')
    query=request.args.get('query')
    
    section=Section.query.all()
    
    my_books=Mybook.query.filter_by(user_id=session['user_id']).all()
    
    mybooks=[book.book_id for book in my_books]
    
    parameters={
        'sname':'Section Name',
        'bkname':'Book Name',
        'aname':'Author Name',
        'price':'Price',
        'pages':'Pages'
    }
    
    if parameter=='sname':
        query=query.lower()
        section=Section.query.filter(Section.name.ilike(f'%{query}%')).all()
        return render_template('library.html',sections=section, myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,query=query,mybooks=mybooks)
    elif parameter=='aname':
        query=query.lower()
        secti=[]
        for sect in section:
            for book in sect.books:
                if query.lower() in book.author_name.lower():
                    secti.append(sect)
                    break
        return render_template('library.html',sections=secti,param=parameter,aname=query, myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,query=query,mybooks=mybooks) 
    elif parameter=='bkname':
        query=query.lower()
        secti=[]
        bookies=[]
        for sect in section:
            for book in sect.books:
                if query.lower() in book.bname.lower():
                    secti.append(sect)
                    break
        return render_template('library.html',sections=secti,param=parameter,bkname=query,myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,query=query,mybooks=mybooks) 
    elif parameter=='price':
        query=float(query)
        secti=[]
        bookies=[]
        for sect in section:
            for book in sect.books:
                if query>=book.price:
                    secti.append(sect)
                    break
        return render_template('library.html',sections=secti,param=parameter,price=query,myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,query=query,mybooks=mybooks)
    elif parameter=='pages':
        query=int(query)
        secti=[]
        bookies=[]
        for sect in section:
            for book in sect.books:
                if query>=book.pages:
                    secti.append(sect)
                    break
        return render_template('library.html',sections=secti,param=parameter,pages=query,myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,query=query,mybooks=mybooks) 
    
    section=Section.query.all()
    
    return render_template('library.html',user=user,sections=section,myrequested_books= myrequested_books,requested_books=requested_books,parameters=parameters,mybooks=mybooks)

@app.route('/request_book/<int:book_id>')
@auth_required  
def request_book(book_id):
    user=User.query.get(session['user_id'])
    book=Book.query.get(book_id)
    requests=BookRequest.query.filter_by(user_id=session['user_id'],book_id=book_id).first()
    if requests:
        flash('Book already requested!')
        return redirect(url_for('library'))
    return render_template('request.html',user=user,book=book)
    
@app.route('/request_book/<int:book_id>',methods=['POST'])
@auth_required  
def request_book_post(book_id):
    user=User.query.get(session['user_id'])
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    books_count = Book.query.filter_by(user_id=session['user_id']).count()
    if books_count==5:
        flash('You have reached the maximum limit of books allowed to take')
        return redirect(url_for('library'),user=user)
    mybook=BookRequest.query.filter_by(user_id=session['user_id'],book_id=book_id).first()
    if not mybook:
        request_date = date.today()
        mybook=BookRequest(user_id=user.id,book_id=book_id,request_date=request_date)
        book.request_counts+=1
        db.session.add(mybook)
    db.session.commit()
    return redirect(url_for('library'))
    
@app.route('/mybooks/<int:book_id>/return')
@auth_required 
def return_book_user(book_id):
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    return render_template('return.html', book= book)

@app.route('/mybooks/<int:book_id>/return',methods=['POST'])
@auth_required 
def return_book_user_post(book_id):
    
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    
    userbook = Mybook.query.filter_by(book_id=book_id).first()
    
    if not userbook:
        flash('You have not taken any book.')
        return redirect(url_for('library'))
    
    db.session.delete(userbook)
    
    book.issue_date = None
    book.return_date = None
    book.user_id = None
    
    requests=BookRequest.query.filter_by(user_id=session['user_id'],book_id=book_id).all()
    
    for request in requests:
        db.session.delete(request)
        db.session.commit()    
    
    db.session.commit()
    
    return redirect(url_for('mybooks'))

@app.route('/mybooks')
@auth_required 
def mybooks():
    mybooks = Mybook.query.filter_by(user_id=session['user_id']).all()
    user_books = [Book.query.get(mybook.book_id) for mybook in mybooks]
    today=date.today()
    if not user_books:
        flash('You have not taken any books')
        return redirect(url_for('library'))
    for book in mybooks:
        if book.return_date==today:
            db.session.delete(book)
            db.session.commit()
    for book in user_books:
        if book.return_date==today:
            book.issue_date=None
            book.return_date=None
            book.user_id=None
            db.session.commit()
    return render_template('mybooks.html', mybooks=mybooks, user_books=user_books)


@app.route('/mybooks/<int:book_id>/feedback')
@auth_required
def feedback(book_id):
    user=User.query.get(session['user_id'])
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    find=UserFeedback.query.filter_by(user_id=user.id,book_id=book.id).first()
    if find:
        flash('Feedback already given for the book')
        return redirect(url_for('mybooks'))
    return render_template('feedback.html',book=book)

@app.route('/mybooks/<int:book_id>/feedback',methods=['POST'])
@auth_required
def feedback_post(book_id):
    user=User.query.get(session['user_id'])
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    
    today=date.today()
    ratings=request.form.get('rating')
    comments=request.form.get('comments')
    
    userfeedback=UserFeedback(user_id=user.id,book_id=book.id,rating=ratings,comment=comments,submitted_at=today)
    
    db.session.add(userfeedback)
    
    db.session.commit()
    
    return redirect(url_for('mybooks'))

@app.route('/mybooks/<int:book_id>/read')
@auth_required
def read(book_id):
    user=User.query.get(session['user_id'])
    book=Book.query.get(book_id)
    return render_template('read.html',book=book)

@app.route('/library/<int:book_id>/buy')
@auth_required
def buy(book_id):
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    return render_template('book/buy.html',book=book)

@app.route('/library/<int:book_id>/buy',methods=['POST'])
@auth_required
def buy_post(book_id):
    book=Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))

    return redirect(url_for('download',book_id=book.id))

@app.route('/mybooks/<int:book_id>/download')
@auth_required
def download(book_id):
    book=Book.query.get(book_id)
    
    if not book:
        flash('Book does not exist')
        return redirect(url_for('library'))
    show_nav=True
    html_content = render_template('download.html',show_nav=show_nav, book=book)
    
    pdf = HTML(string=html_content).write_pdf()

   
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={book.bname}.pdf'
    
    return response




