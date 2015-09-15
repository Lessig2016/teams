# teams

The backend app that powers [team.lessig2016.us](https://team.lessig2016.us)

Report improvements/bugs at https://github.com/inmomentsoftware/teams/issues.


## Design Docs

Based on Mayday's teams project.
Please see https://github.com/MayOneUS/wiki/wiki/My-SuperPAC-design-doc.


## Setup

1. `cp config_NOCOMMIT_README config_NOCOMMIT.py`
2. download and setup [Google App Engine for Python here](https://developers.google.com/appengine/downloads)
3. Run this app with `dev_appserver.py .`
4. If you want to run [inmomentsoftware/lessigpledge](https://github.com/inmomentsoftware/lessigpledge) simultaneously, which you
   will need to for testing submission of forms and other things, run this app on a separate port other than the
   default 8080 to avoid port collisions. This can done by running
   `dev_appserver.py --port SOME_OTHER_FREE_PORT_LIKE_8081 .`.

## Deploy

1. Uncomment the following two lines in config_NOCOMMIT.py
```
## For production.
auth_service = ProdAuthService("https://auth.lessig2016.us")
pledge_service = ProdPledgeService(PLEDGE_SERVICE_URL)
```
2. Run `appcfg.py update .` in the root directory of the repo.

## Code of Conduct

The Lessig Equal Citizens Exploratory Committee is committed to fostering an open and inclusive community where engaged, dedicated volunteers can build the strategy and tools necessary to fix our country's democracy. All members of the community are expected to behave with civility, speak honestly and treat one another respectfully.

This project adheres to the [Open Code of Conduct](http://todogroup.org/opencodeofconduct/#Lessig2016/conduct@lessigforpresident.com). 
By participating, you are expected to honor this code.

This reference as well as the included copy of the [Code of Conduct](https://github.com/Lessig2016/teams/blob/master/CONDUCT.md)
shall be included in all forks and distributions of this repository.

## Legal

The Lessig campaign is not responsible for the content posted to this repository, or for actions taken or liabilities incurred by one or more group members. 

You may not post content to the repository that you do not own, and by posting content you consent to its use by others, including the campaign. 

You are responsible for your compliance with federal campaign finance laws. You may not, for example, volunteer for the campaign if you are being paid by someone else to do so, or volunteer while at work unless it is limited to a few hours per month and your volunteering doesn’t create additional costs for your employer.

The campaign may remove any offensive, abusive, attacking, or discriminatory content, as well as any content that may otherwise violate our [Terms of Service](https://lessig2016.us/terms-of-service/). 

## Copyright and License

Copyright 2015 Lessig Equal Citizens Exploratory Committee. This 
project is released under [GNU Affero General Public License, version 3](https://github.com/Lessig2016/teams/blob/master/LICENSE).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
