import webapp2
import jinja2
import os
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

class Handler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.write(*a,**kw)
	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(params)
	def render(self,template,**kw):
		self.write(self.render_str(template,**kw))
class Blog(db.Model):
	
	id = db.IntegerProperty()
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)
	
	def render(self):
		self._render_text = self.content.replace('\n','<br>')
		return render('post.htm', p=self)
	

class MainHandler(Handler):
		
	def get(self):
		self.redirect('/blog')

class BlogHandler(Handler):
	def get(self):
		#query the available blogs
		blogs = db.GqlQuery('SELECT * FROM Blog ORDER BY created DESC LIMIT 10 ')
		self.render('blog.html',blog_posts=blogs)
def blog_key(name='default'):
	return db.Key.from_path('blogs',name)
class NewPost(Handler):
	def new_post(self,subject="",content="",error=""):
		
		self.render("new_post.html",subject=subject,content=content,error=error)
	def get(self):
		self.new_post()
		
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
    ('/', MainHandler),('/blog',BlogHandler),('/new_post',NewPost),('/blog/([0-9]+)',BlogPage)
], debug=True)
