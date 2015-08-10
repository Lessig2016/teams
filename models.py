from google.appengine.ext import db

class Team(db.Model):
  CURRENT_VERSION = 2

  primary_slug = db.StringProperty()
  title = db.StringProperty(required=True)
  description = db.TextProperty(required=True)

  total_people_joined = db.IntegerProperty(default=0)
  goal_dollars = db.IntegerProperty()
  youtube_id = db.StringProperty()
  zip_code = db.StringProperty()

  # for use with google.appengine.api.images get_serving_url
  image = db.BlobProperty()
  gravatar = db.StringProperty()

  user_token = db.StringProperty()

  team_version = db.IntegerProperty(default=1)

  creation_time = db.DateTimeProperty(auto_now_add=True)
  modification_time = db.DateTimeProperty(auto_now=True)

  @classmethod
  def create(cls, **kwargs):
    kwargs["team_version"] = cls.CURRENT_VERSION
    team = cls(**kwargs)
    team.put()
    return team

class Slug(db.Model):
  # the key is the slug name
  team = db.ReferenceProperty(Team, required=True)

  @staticmethod
  @db.transactional
  def _make(full_slug, team):
    e = Slug.get_by_key_name(full_slug)
    if e is not None:
      return False
    Slug(key_name=full_slug, team=team).put()
    return True

  @staticmethod
  def new(team):
    slug_name = MULTIDASH_RE.sub('-', INVALID_SLUG_CHARS.sub('-', team.title))
    slug_name = slug_name.rstrip('-')
    token_amount = SLUG_TOKEN_AMOUNT
    while True:
      slug_prefix = os.urandom(token_amount).encode('hex')
      token_amount += 1
      full_slug = "%s-%s" % (slug_prefix, slug_name)
      if Slug._make(full_slug, team):
        return full_slug


class AdminToTeam(db.Model):
  """This class represents an admin to team relationship, since it's
  many-to-many
  """
  user = db.StringProperty(required=True)  # from current_user["user_id"]
  team = db.ReferenceProperty(Team, required=True)

  @staticmethod
  def memcacheKey(user_id, team):
    return repr((str(user_id), str(team.key())))



