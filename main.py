import webapp2
import jinja2
import os
import hmac
import hashlib
import string
import re
import random
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

#secret key for creating values
secret_key = '0!`~|+=_(*%:?>,$@-19'

#letter to be used in creating salt
letters = string.ascii_letters

#convenience function for setting and validating values
def set_secure_val(val):
	return '%s|%s' %(val,hmac.new(secret_key,str(val)).hexdigest())

def check_secure_val(secure_val):
	val = secure_val.split('|')[0]
	return val and secure_val==set_secure_val(val)
class Handler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.write(*a,**kw)
	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(params)
	def render(self,template,**kw):
		self.write(self.render_str(template,**kw))
	
	#convenience functions for creating and verifying cookie
	def make_secure_cookie(self,name,user_id):
		return self.response.headers.add_header('Set-Cookie','%s=%s; path=/' %(name,set_secure_val(user_id)))
	def check_secure_cookie(self,name):
		secure_cookie = self.request.cookies.get(name)
		return secure_cookie and check_secure_val(secure_cookie)
	
	#convenience functions for hashing password
	def make_salt(self,length=5):
		return ''.join(random.choice(letters) for x in xrange(length))
	def make_pw_hash(self,name,password, salt=None):
		if not salt:
			salt = self.make_salt()
		return '%s,%s' %(salt,hashlib.sha256(name + password + salt).hexdigest())
	def valid_pw(self,name,password,hash):
		salt = hash.split(',')[0]
		return salt and hash == self.make_pw_hash(name,password,salt)
def blog_key(name='default'):
	return db.Key.from_path('blogs',name)

#parent key for users
def user_key(name='user-parent'):
	return db.Key.from_path('users',name)
def comment_key(name='comment'):
	return db.Key.from_path('comment',name)


class User(db.Model):
	
	name = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty(required = True)
	def by_id(self,uid):
		return self.get_by_id(uid)
class Blog(db.Model):
	
	id = db.IntegerProperty()
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)
	author = db.StringProperty()
	
	def by_id(self,blog_id):
		return self.get_by_id(blog_id)
	
	
	def render(self):
		self._render_text = self.content.replace('\n','<br>')
		return render('post.htm', p=self)
class Comment(db.Model):
	post_id = db.StringProperty(required=True)
	commentor = db.ReferenceProperty(User)
	commentor_id = db.StringProperty(required = True)
	comment = db.TextProperty(required=True)
	date = db.DateTimeProperty(auto_now_add = True)
	
class Like(db.Model):
	post_id = db.StringProperty(required = True)
	liked_by_id = db.StringProperty(required = True)
	liked_by = db.ReferenceProperty(User)
	date_like = db.DateTimeProperty(auto_now_add = True)
	

class MainHandler(Handler):
		
	def get(self):
		self.redirect('/blog')

class BlogHandler(Handler):
	def post_to_blog(self,comment=None):
		#query the available blogs
		blogs = db.GqlQuery('SELECT * FROM Blog ORDER BY created DESC LIMIT 10 ')
		comments = Comment.all().fetch(limit=10)
		cookie = self.request.cookies.get('user_id')
		if cookie:
			uid = cookie.split('|')[0]
			user = User.get_by_id(int(uid),parent=user_key())
			self.render('blog.html',blog_posts=blogs, user=user.name, login=True,comments = comments)
		else:
			self.render('blog.html',blog_posts=blogs,comments = comments)
	def get(self):
		self.post_to_blog()
	def post(self):
		comment = self.request.get('comment')
		id_post = self.request.get('post_id')
		if comment:
			cookie = self.request.cookies.get('user_id')
			uid = cookie.split('|')[0]
			commentor = User.get_by_id(int(uid) ,parent=user_key())
			if id_post:
				cmnt = Comment(parent=comment_key(),commentor=commentor,commentor_id=uid, comment = comment, post_id = id_post)
				cmnt.put()
				load_comments = db.GqlQuery('SELECT * FROM Comment ORDER BY date DESC LIMIT 10 ')
				self.post_to_blog(load_comments)
			else:
				self.post_to_blog();
		else:
			pass
class Signup(Handler):
	def get(self):
		self.render('signup.html')
	def post(self):
		
		#get params from request
		
		username = self.request.get("username")
		password = self.request.get("userpass")
		confirm = self.request.get("confirm")
		email = self.request.get("email")
		
		#query db for existing user
		#user = db.GqlQuery('SELECT * FROM User WHERE name= :1',username)
		user = User.all().filter('name =', username).get()
		
		if not user:
			#validate the params
			user_empty = check_empty(self,username)
			user_err = check_username(self,username)
			empty_pass = check_empty(self,password)
			empty_confirm = check_empty(self,confirm)
			confirm_err = confirmPass(self,password,confirm)
			email_err = validate_email(self,email)
			
			if (user_empty or empty_pass or empty_confirm):
				self.render('signup.html',user_err=user_empty,confirm_err=empty_confirm,email_err="")
			else:
				if (user_err or confirm_err or email_err):
					self.render('signup.html',user_err=user_err,confirm_err=confirm_err,email_err=email_err)
				else:
					#self.response.headers.add_header('Set-Cookie','username='+str(username)+',path=/')
					
					user = User(parent=user_key(),name=username, email=email,password=self.make_pw_hash(username,password))
					
					user.put()
					self.make_secure_cookie('user_id',user.key().id())
					self.redirect('blog')
		else:
			user_err="Username already exists!"
			self.render('signup.html',user_err=user_err,confirm_err="",email_err="")
class LoginHandler(Handler):
	def get(self):
		self.render('login.html',error='')
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		
		user = db.GqlQuery('SELECT * FROM User WHERE name = :user', user=username)
		if user.get():
			if (self.valid_pw(username,password,user.get().password)):
				cookie = self.make_secure_cookie('user_id',str(user.get().key().id()))
				self.render('blog.html', blog_posts = Blog.all(),user=user.get().name, login=True)
			else:
				self.render('login.html',error='Invalid Password!')
		else:
			self.render('login.html',error='User does not exist!')

class Logout(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie','user_id =; path=/')
		self.redirect('blog')
	
class NewPost(Handler):
	
	def new_post(self,subject="",content="",error=""):
		if self.check_secure_cookie('user_id'):
			self.render("new_post.html",subject=subject,content=content,error=error)
		else:
			self.render('login.html',error='Please login to continue')
	def get(self):
		if self.check_secure_cookie('user_id'):
		
			self.new_post()
		else:
			self.render('login.html',error='Please login to continue')
		
	def post(self):
		cookie = self.request.cookies.get('user_id')
		if cookie:
			subject = self.request.get("subject")
			content = self.request.get("content")
			content = content.replace('\n','<br>')
			if subject and content:
				
				blog = Blog(parent=blog_key(),subject=subject,content=content,author=User.get_by_id(long(cookie.split('|')[0]),parent=user_key()).name)
				blog.put()
				self.redirect('/blog/%s' % str(blog.key().id()))
			else:
				error = "Sorry, no field can be left empty!"
				self.new_post(subject,content,error)
		self.render('login.html',error='Please login to continue')

class BlogPage(BlogHandler):
	def get(self,post_id):
		key = db.Key.from_path('Blog',int(post_id),parent=blog_key())
		post = db.get(key)
		if not post:
			self.error(404)
			return
			
		self.render('post.html',posts=post)
'''
class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Blog', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("post.html", post = post)
	
'''
def check_empty(self,input):
	if not input:
		return "This field cannot be empty!"
	else:
		return ""
def confirmPass(self,pass1,pass2):
	if(pass1 == pass2):
		return ""
	else:
		return "Passwords do not match!"
def check_username(self,input):
	if ((" " in input) or len(input)<3):
		return "Invalid Username!"
	else:
		return ""
def validate_email(self,email):
	if re.match("^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email) or not email:
		return ""
	else:
		return "Invalid email address!"
app = webapp2.WSGIApplication([
    ('/', MainHandler),('/blog',BlogHandler),('/new_post',NewPost),('/blog/([0-9]+)',BlogPage),('/login',LoginHandler),('/signup',Signup),('/logout',Logout)
], debug=True)
