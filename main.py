import webapp2
import jinja2
import os
import hmac
import hashlib
import string
import random
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

#secret key for creating values
secret_key = '0!`~|+=_(*%:?>,$@-19'

#letter to used in creating salt
letters = string.ascii_letters

#convenience function for setting and validating values
def set_secure_val(val):
	return '%s|%s' %(val,hmac.new(secret_key,val).hexdigest())

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
		return self.response.headers.add_header('Set-Cookies','%s=%s, path=/' %(name,set_secure_val(user_id)))
	def check_secure_cookie(self,secure_cookie):
		val = secure_cookie.split('|')[0]
		return val and check_secure_val(val)
	
	#convenience functions for hashing password
	def make_salt(length=5):
		return ''.join(random.choice(letters) for x in xrange(length))
	def make_pw_hash(self,name,password, salt=None):
		if not salt:
			salt = make_salt()
		return '%s,%s' %(salt,hashlib.sha256(name + password + salt).hexdigest())
	def valid_pw(self,name,password,hash):
		salt = hash.split(',')[0]
		return salt and hash == make_pw_hash(name,password,salt)
def blog_key(name='default'):
	return db.Key.from_path('blogs',name)

#parent key for users
def user_key(name='user-parent'):
	return db.Key.from_path('users',name)
class Blog(db.Model):
	
	id = db.IntegerProperty()
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)
	author_id = db.StringProperty(required =True)
	
	def by_id(self,blog_id):
		return self.get_by_id(blog_id)
	
	
	def render(self):
		self._render_text = self.content.replace('\n','<br>')
		return render('post.htm', p=self)

class Users(db.Model):
	
	name = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty(required = True)
	def by_id(self,uid):
		return self.get_by_id(uid)
	

class MainHandler(Handler):
		
	def get(self):
		self.redirect('/blog')

class BlogHandler(Handler):
	def get(self):
		#query the available blogs
		blogs = db.GqlQuery('SELECT * FROM Blog ORDER BY created DESC LIMIT 10 ')
		self.render('blog.html',blog_posts=blogs)
class Signup(Handler):
	def get(self):
		self.render('signup.html')
class LoginHandler(Handler):
	def post(self):
		
		#get params from request
		global username
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
					self.set_secure_cookie('user_id',user.key().id())
					self.redirect('welcome')
		else:
			user_err="Username already exists!"
			self.render('signup.html',user_err=user_err,confirm_err="",email_err="")


	
class NewPost(Handler):
	def new_post(self,subject="",content="",error=""):
		
		self.render("new_post.html",subject=subject,content=content,error=error)
	def get(self):
		if self.check_secure_cookie('user_id'):
		
			self.new_post()
		else:
			self.render('login.html',error='Please login to continue')
		
	def post(self):
		
		subject = self.request.get("subject")
		content = self.request.get("content")
		content = content.replace('\n','<br>')
		if subject and content:
			blog = Blog(parent=blog_key(),subject=subject,content=content)
			blog.put()
			self.redirect('/blog/%s' % str(blog.key().id()))
		else:
			error = "Sorry, no field can be left empty!"
			self.new_post(subject,content,error)

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
app = webapp2.WSGIApplication([
    ('/', MainHandler),('/blog',BlogHandler),('/new_post',NewPost),('/blog/([0-9]+)',BlogPage),('/login',LoginHandler),('signup',Signup)
], debug=True)
