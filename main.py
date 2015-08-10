import csv
import functools
import hashlib
import json
import os
import re
import urllib
import urlparse
import logging
import traceback

import jinja2
import markdown
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch

import config_NOCOMMIT

from util import leaderboardGetter

JINJA = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates/'),
  extensions=['jinja2.ext.autoescape'],
  autoescape=True)
JINJA.filters["urlencode"] = \
    lambda s: urllib.quote(s.encode('ascii', errors='ignore'), safe="")

YOUTUBE_ID_VALIDATOR = re.compile(r'^[\w\-]+$')
INVALID_SLUG_CHARS = re.compile(r'[^\w-]')
MULTIDASH_RE = re.compile(r'-+')
SLUG_TOKEN_AMOUNT = 2

DEFAULT_TITLE = ""

DEFAULT_DESC = u"""\
The American political system is broken. So broken that it cannot be fixed \
by any normal process. That's why I'm supporting Lessig for President in 2016.

Every other candidate is handcuffed by the political system, so Lessig \
is running for office to pass one bill - the Equal Citizens Act of 2017 - \
that will fundamentally transform our government. And then, after the bill \
becomes law, he will resign and the vice president will take the office of \
president.

Running a political campaign isn't cheap, especially running for president. \
It's estimated that the final Republican and Democratic candidates will \
spend over $1 billion EACH! So this campaign needs your help.

Elections should be decided on one person, one vote. That's why I'm \
writing to my friends and family to ask you to contribute. Please join \
me and support Lessig 2016.
"""

PREVIOUS_PLEDGE_DESC = DEFAULT_DESC + u"""\

{signature}
"""

DEFAULT_THANKYOU_SUBJECT = u"""
Thank You For Pledging to My Lessig 2016 Page
"""

DEFAULT_THANKYOU_MESSAGE = u"""
Thank you for pledging in support of Lessig's 2016 campaign for Equal Citizens. \

You can reach me by replying to this email.
"""


class BaseHandler(webapp2.RequestHandler):
  def dispatch(self, *args, **kwargs):
    if self.request.host == "lessigforpresident.com" and self.request.method == "GET":
      self.request.host = "team.lessigforpresident.com"
      return self.redirect(self.request.url)
    return webapp2.RequestHandler.dispatch(self, *args, **kwargs)

  @webapp2.cached_property
  def auth_response(self):
    if config_NOCOMMIT.auth_service.requires_https:
      self.request.scheme = "https"
    return config_NOCOMMIT.auth_service.getAuthResponse(
        self.request.cookies.get("auth", ""), self.request.url)

  @property
  def logged_in(self):
    return self.auth_response["logged_in"]

  @property
  def current_user(self):
    return self.auth_response.get("user")

  @property
  def login_links(self):
    return self.auth_response.get("login_links") or {}

  @property
  def logout_link(self):
    if config_NOCOMMIT.auth_service.requires_https:
      self.request.scheme = "https"
    return config_NOCOMMIT.auth_service.getLogoutLink(self.request.url)

  @property
  def pledge_root_url(self):
    return config_NOCOMMIT.PLEDGE_SERVICE_URL

  def render_template(self, template, **kwargs):
    if self.logged_in:
      data = {
        "logged_in": True,
        "current_user": self.current_user,
        "logout_link": self.logout_link,
        "pledge_root_url": self.pledge_root_url,
        "current_url": self.request.url}
    else:
      data = {
        "logged_in": False,
        "login_links": self.login_links,
        "pledge_root_url": self.pledge_root_url,
        "current_url": self.request.url}
    data.update(kwargs)
    self.response.write(JINJA.get_template(template).render(data))

  def notfound(self):
    self.response.status = 404
    self.render_template("404.html")




def require_login(fn):
  @functools.wraps(fn)
  def new_handler(self, *args, **kwargs):
    if not self.logged_in:
      self.redirect("/")
      return
    return fn(self, *args, **kwargs)
  return new_handler


class IndexHandler(BaseHandler):
  def get(self):
    if self.logged_in:
      return self.redirect("/dashboard")
    return self.redirect("/login")
          
class LeaderboardHandler(BaseHandler):
  def get(self):
    offset = int(self.request.get("offset") or 0)
    limit = int(self.request.get("limit") or 25)
    orderBy = self.request.get("orderBy") or "-totalCents"
        
    teams, prev_link, next_link = leaderboardGetter(offset, limit, orderBy)
    self.render_template("leaderboard.html", teams=teams,
        prev_link=prev_link, next_link=next_link, orderBy=orderBy)


class LoginHandler(BaseHandler):
  def get(self):    
    if self.logged_in:
      return self.redirect("/dashboard")
    
    offset = int(self.request.get("offset") or 0)
    limit = int(self.request.get("limit") or 5)
    orderBy = self.request.get("orderBy") or "-num_pledges"
    
    teams, prev_link, next_link = leaderboardGetter(offset, limit, orderBy)

    self.render_template("login.html", teams=teams,
        prev_link=prev_link, next_link=next_link, orderBy=orderBy)

class NotFoundHandler(BaseHandler):
  def get(self):
    self.notfound()


def isUserAdmin(user_id, team):
  return (memcache.get(AdminToTeam.memcacheKey(user_id, team)) or
          (AdminToTeam.all().filter("team =", team).filter(
              "user =", user_id).get() is not None))


def makeUserAdmin(user_id, team):
  AdminToTeam(user=user_id, team=team).put()
  memcache.add(AdminToTeam.memcacheKey(user_id, team), True, 30)


class TeamBaseHandler(BaseHandler):
  def validate(self, slug):
    s = Slug.get_by_key_name(slug)
    if s is None:
      self.notfound()
      return None, False, False
    team = s.team
    if team is None:
      self.notfound()
      return None, False, False
    primary = True
    if team.primary_slug and team.primary_slug != slug:
      primary = False
    is_admin = False
    if self.logged_in:
      if isUserAdmin(self.current_user["user_id"], team):
        is_admin = True
    return team, primary, is_admin


class TeamHandler(TeamBaseHandler):
  def get(self, slug):
    team, primary, is_admin = self.validate(slug)
    if team is None:
      return
    if not primary:
      return self.redirect("/t/%s" % team.primary_slug, permanent=True)
    if is_admin:
      edit_url = "/t/%s/edit" % team.primary_slug
      thank_url = "/t/%s/thank" % team.primary_slug
    else:
      edit_url = None
      thank_url = None
    self.render_template(
        "show_team.html", team=team, edit_url=edit_url, thank_url=thank_url,
        description_rendered=markdown.markdown(
            jinja2.escape(team.description)))

class TeamHandler2(TeamBaseHandler):
  def get(self, slug):
    team, primary, is_admin = self.validate(slug)
    if team is None:
      return
    if not primary:
      return self.redirect("/t/%s" % team.primary_slug, permanent=True)
    if is_admin:
      edit_url = "/t/%s/edit" % team.primary_slug
      thank_url = "/t/%s/thank" % team.primary_slug
    else:
      edit_url = None
      thank_url = None
    self.render_template(
        "show_team2.html", team=team, edit_url=edit_url, thank_url=thank_url,
        description_rendered=markdown.markdown(
            jinja2.escape(team.description)))

class ShareTeamHandler(TeamBaseHandler):
  def get(self, slug):
    team, primary, is_admin = self.validate(slug)
    if team is None:
      return
    else:
      team_url = "https://team.lessigforpresident.com/t/" + team.primary_slug
      self.render_template(
          "share_team.html", team=team, team_url=team_url)


class DashboardHandler(BaseHandler):
  @require_login
  def get(self):
    teams = [a.team for a in
             AdminToTeam.all().filter('user =',
                self.current_user["user_id"])]
    self.render_template("dashboard.html", teams=teams)


class NewTeamHandler(BaseHandler):
  @require_login
  def get(self):
    self.render_template("new_team.html", form=TeamForm())

  @require_login
  def post(self):
    form = TeamForm(self.request.POST)
    if not form.validate():
      return self.render_template("new_team.html", form=form)
    team = Team.create(title=form.title.data,
                       description=form.description.data,
                       goal_dollars=form.goal_dollars.data,
                       youtube_id=form.youtube_id.data,
                       zip_code=form.zip_code.data)
    # TODO: can i reference a team before putting it in other reference
    # properties? should check
    team.primary_slug = Slug.new(team)    
    try:
      result = config_NOCOMMIT.pledge_service.updateMailchimp(team) 
    except Exception as e:
      logging.error('Exception updating mailChimp: ' + str(e))
      logging.info(traceback.format_exc())

    team.put()
    makeUserAdmin(self.current_user["user_id"], team)
    return self.redirect("/t/%s" % team.primary_slug)


class FromPledgeBaseHandler(BaseHandler):
  def add_to_user(self, team):
    if self.logged_in:
      if not isUserAdmin(self.current_user["user_id"], team):
        makeUserAdmin(self.current_user["user_id"], team)


class NewFromPledgeHandler(FromPledgeBaseHandler):
  def get(self, user_token):
    team = Team.all().filter('user_token =', user_token).get()
    if team is None:
      user_info = config_NOCOMMIT.pledge_service.loadPledgeInfo(user_token)
      if user_info is None:
        return self.notfound()
      user_pledge_dollars = int(user_info["pledge_amount_cents"]) / 100
      goal_dollars = user_pledge_dollars * 10
      if user_info["name"]:
        signature = "_Thank you,_\n\n_%s_" % user_info["name"]
      else:
        signature = "Thank you!"
      title = user_info["name"] or DEFAULT_TITLE
      form = TeamForm(data={
          "goal_dollars": str(goal_dollars),
          "title": title,
          "zip_code": str(user_info["zip_code"] or ""),
          "description": PREVIOUS_PLEDGE_DESC.format(
              pledge_dollars=user_pledge_dollars,
              signature=signature,
              title=title)})
    else:
      self.add_to_user(team)
      form = TeamForm(obj=team)
    self.render_template("new_from_pledge.html", form=form)

  def post(self, user_token):
    team = Team.all().filter('user_token =', user_token).get()
    if team is None:
      # just make sure this pledge exists
      user_info = config_NOCOMMIT.pledge_service.loadPledgeInfo(user_token)
      if user_info is None:
        return self.notfound()
    form = TeamForm(self.request.POST, team)
    if not form.validate():
      return self.render_template("new_from_pledge.html", form=form)
    if team is None:
      gravatar = "https://secure.gravatar.com/avatar/%s?%s" % (
        hashlib.md5(user_info['email'].lower()).hexdigest(),
        urllib.urlencode({'s': str('120')}))
      team = Team.create(title=form.title.data,
                         description=form.description.data,
                         zip_code=form.zip_code.data,
                         user_token=user_token,
                         gravatar=gravatar)
    else:
      form.populate_obj(team)
    self.add_to_user(team)
    team.primary_slug = Slug.new(team)  
    try:
      result = config_NOCOMMIT.pledge_service.updateMailchimp(team) 
    except Exception as e:
      logging.error('Exception updating mailChimp: ' + str(e))
      logging.info(traceback.format_exc())
    team.put()
    if self.logged_in:
      return self.redirect("/t/%s" % team.primary_slug)
    return self.redirect("/dashboard/add_admin_from_pledge/%s" % user_token)


class AddAdminFromPledgeHandler(FromPledgeBaseHandler):
  def get(self, user_token):
    team = Team.all().filter('user_token =', user_token).get()
    if team is None:
      return self.notfound()
    if not self.logged_in:
      return self.render_template("add_admin_login.html", team=team)
    self.add_to_user(team)
    return self.redirect("/t/%s" % team.primary_slug)


class EditTeamHandler(TeamBaseHandler):
  # require_login unneeded because we do the checking ourselves with validate
  def get(self, slug):
    team, primary, is_admin = self.validate(slug)
    if team is None:
      return
    if not primary:
      return self.redirect("/t/%s/edit" % team.primary_slug, permanent=True)
    if not is_admin:
      return self.redirect("/t/%s" % team.primary_slug)
    self.render_template("edit_team.html", form=TeamForm(obj=team))

  # require_login unneeded because we do the checking ourselves with validate
  def post(self, slug):
    team, _, is_admin = self.validate(slug)
    if team is None:
      return
    if not is_admin:
      return self.redirect("/t/%s" % team.primary_slug)
    form = TeamForm(self.request.POST, team)
    if not form.validate():
      return self.render_template("edit_team.html", form=form)
    form.populate_obj(team)
    team.primary_slug = Slug.new(team)
    try:
      result = config_NOCOMMIT.pledge_service.updateMailchimp(team) 
    except Exception as e:
      logging.error('Exception updating mailChimp: ' + str(e))
      logging.info(traceback.format_exc())
  
    team.put()
    self.redirect("/t/%s" % team.primary_slug)


class ThankTeamHandler(TeamBaseHandler):
  # require_login unneeded because we do the checking ourselves with validate
  def get(self, slug):
    team, primary, is_admin = self.validate(slug)
    if team is None:
      return
    if not primary:
      return self.redirect("/t/%s/edit" % team.primary_slug, permanent=True)
    if not is_admin:
      return self.redirect("/t/%s" % team.primary_slug)
    self.render_template("thank_team.html", form=ThankYouForm(obj=team))

  # require_login unneeded because we do the checking ourselves with validate
  def post(self, slug):
    team, _, is_admin = self.validate(slug)
    if team is None:
      return
    if not is_admin:
      return self.redirect("/t/%s" % team.primary_slug)
    form = ThankYouForm(self.request.POST)
    if not form.validate():
      return self.render_template("thank_team.html", form=form)

    data = form.data.copy()
    data["team"] = team.key()

    payload = urllib.urlencode(data)

    url = self.pledge_root_url + "/r/thank"

    result = urlfetch.fetch(url=url,
      payload=payload,
      method=urlfetch.POST,
      validate_certificate=False)


    if result.status_code == 200:
      response_data = json.loads(result.content)
      num_emailed = response_data["num_emailed"]
      total_pledges = response_data["total_pledges"]

      return self.render_template("thank_team_success.html",
        num_emailed=num_emailed,
        total_pledges=total_pledges,
        team_url="/t/%s" % team.primary_slug)
    else:
      return self.render_template("thank_team.html", form=form, error=result.content)


class AdminHandler(webapp2.RequestHandler):
  def render_template(self, template, **data):
    self.response.write(JINJA.get_template(template).render(data))


class SiteAdminIndex(AdminHandler):
  def get(self):
    self.render_template("site_admin.html")


class SiteAdminCSV(AdminHandler):
  def get(self):
    self.render_template("site_csv.html")


class SiteAdminTeams(AdminHandler):
  def get(self):
    query = Team.all()
    cursor = self.request.get("cursor")
    if cursor:
      query.with_cursor(cursor)
    teams = []
    for team in query.fetch(int(self.request.get("amount", 100))):
      teams.append({
          "key": str(team.key()),
          "title": team.title,
          "slug": team.primary_slug,
          "url": "%s/t/%s" % (self.request.application_url, team.primary_slug),
          "zip_code": team.zip_code,
          "user_token": team.user_token,
          "crtime": str(team.creation_time),
          "mtime": str(team.modification_time),
          "version": team.team_version})
    cursor = query.cursor()
    self.response.write(json.dumps({
        "next_cursor": cursor,
        "teams": teams}))


app = webapp2.WSGIApplication(config_NOCOMMIT.auth_service.handlers() + [
  (r'/t2/([^/]+)/?', TeamHandler),
  (r'/t/([^/]+)/?', TeamHandler2),
  (r'/t/([^/]+)/edit?', EditTeamHandler),
  (r'/t/([^/]+)/share?', ShareTeamHandler),
  (r'/t/([^/]+)/thank?', ThankTeamHandler),
  (r'/login/?', LoginHandler),
  (r'/dashboard/?', DashboardHandler),
  (r'/dashboard/new/?', NewTeamHandler),
  (r'/dashboard/new_from_pledge/(\w+)', NewFromPledgeHandler),
  (r'/dashboard/add_admin_from_pledge/(\w+)', AddAdminFromPledgeHandler),
  (r'/site-admin/?', SiteAdminIndex),
  (r'/site-admin/csv/?', SiteAdminCSV),
  (r'/site-admin/teams.json', SiteAdminTeams),
  (r'/?', IndexHandler),
  (r'/leaderboard/?', LeaderboardHandler),
  (r'.*', NotFoundHandler)], debug=False)
