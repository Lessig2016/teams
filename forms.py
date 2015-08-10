import wtforms

from wtforms.fields.html5 import IntegerField
from wtforms.widgets.html5 import URLInput


class YoutubeIdField(wtforms.Field):
  widget = URLInput()

  def __init__(self, label=None, validators=None, **kwargs):
    wtforms.Field.__init__(self, label, validators, **kwargs)

  def _value(self):
    if self.data is not None:
      return u"https://www.youtube.com/watch?v=%s" % unicode(self.data)
    else:
      return ''

  def process_formdata(self, valuelist):
    self.data = None
    if valuelist:
      parsed = urlparse.urlparse(valuelist[0])
      if "youtube.com" not in parsed.netloc:
        raise ValueError(self.gettext("Not a valid Youtube URL"))
      video_args = urlparse.parse_qs(parsed.query).get("v")
      if len(video_args) != 1:
        raise ValueError(self.gettext("Not a valid Youtube URL"))
      youtube_id = video_args[0]
      if not YOUTUBE_ID_VALIDATOR.match(youtube_id):
        raise ValueError(self.gettext("Not a valid Youtube URL"))
      self.data = youtube_id


class ZipcodeField(wtforms.Field):
  """
  A text field, except all input is coerced to an integer.  Erroneous input
  is ignored and will not be accepted as a value.
  """
  widget = wtforms.widgets.TextInput()

  def __init__(self, label=None, validators=None, **kwargs):
    wtforms.Field.__init__(self, label, validators, **kwargs)

  def _value(self):
    if self.data is not None:
      return unicode(self.data)
    else:
      return ''

  def process_formdata(self, valuelist):
    self.data = None
    if valuelist:
      try:
        int(valuelist[0])
      except ValueError:
        self.data = None
        raise ValueError(self.gettext('Not a valid integer value'))
      else:
        self.data = valuelist[0]


class TeamForm(wtforms.Form):
  title = wtforms.StringField("Your Name", [
      wtforms.validators.Length(min=1, max=500)], default=DEFAULT_TITLE)
  description = wtforms.TextAreaField("Your Personal Message",
      [wtforms.validators.Length(min=1)],
      default=DEFAULT_DESC.format(title=DEFAULT_TITLE))

  goal_dollars = IntegerField("Goal", [wtforms.validators.optional()])
  youtube_id = YoutubeIdField("Youtube Video URL", [
      wtforms.validators.optional()])
  zip_code = ZipcodeField("Zip Code", [wtforms.validators.optional()])


class ThankYouForm(wtforms.Form):
  reply_to = wtforms.StringField("Your Email Address", [
    wtforms.validators.Email(message='Please enter a valid email.'),
    wtforms.validators.Length(min=1, max=100)])
  subject = wtforms.StringField("Message Subject", [
      wtforms.validators.Length(min=1, max=150)], default=DEFAULT_THANKYOU_SUBJECT)
  message_body = wtforms.TextAreaField("Message Body",
      [wtforms.validators.Length(min=1, max=10000)],
      default=DEFAULT_THANKYOU_MESSAGE)
  new_members = wtforms.BooleanField("Send to new contributors only (have not \
    previsously received a thank you message)", [], default=True)

