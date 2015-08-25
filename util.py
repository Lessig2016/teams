import urllib

from google.appengine.ext import db

from models import Team

import config_NOCOMMIT

def leaderboardGetter(offset, limit, orderBy):
  leaderboard = config_NOCOMMIT.pledge_service.getLeaderboard(
      offset=offset, limit=limit, orderBy=orderBy)
  def team_iter():
    for team_data in leaderboard:
      if team_data["total_cents"] == 0:
          continue
      if team_data["team"].startswith('{{team.key()}}'):
          # sentinel value == no team
          continue
      team = Team.get(db.Key(team_data["team"]))
      if team is None:
        continue
      yield team_data, team
  teams = []
  for idx, (team_data, team) in enumerate(team_iter()):
    teams.append({
        "amount": int(team_data["total_cents"] / 100),
        "num_pledges":int(team_data["num_pledges"]),
        "title": team.title,
        "primary_slug": team.primary_slug,
        "position": 1 + offset + idx})
  prev_link, next_link = None, None
  if offset > 0:
    prev_link = "?%s" % urllib.urlencode({
        "offset": max(offset - limit, 0),
        "limit": limit,
        "orderBy": orderBy})
  if len(teams) == limit:
    next_link = "?%s" % urllib.urlencode({
        "offset": offset + limit,
        "limit": limit,
        "orderBy": orderBy})
  return teams, prev_link, next_link
