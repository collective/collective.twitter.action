from persistent import Persistent 
from OFS.SimpleItem import SimpleItem

from zope.interface import implements, Interface, alsoProvides
from zope.component import adapts
from zope.formlib import form
from zope import schema
from zope.schema.vocabulary import SimpleVocabulary
from z3c.form import interfaces

from zope.app.component.hooks import getSite
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from plone.registry.interfaces import IRegistry

from zope.component.interfaces import IObjectEvent

from plone.contentrules.rule.interfaces import IExecutable, IRuleElementData
from zope.schema.interfaces import IContextSourceBinder

from plone.app.contentrules.browser.formhelper import AddForm, EditForm 

from Acquisition import aq_inner

from collective.twitter.action import MessageFactory as _

import twitter

# imports for tiny url call
from urllib import urlencode
from urllib2 import urlopen, HTTPError, URLError

def getTinyURL(url):
    """ returns shotend url or None """  
    TINYURL = 'http://tinyurl.com/api-create.php'
    linkdata = urlencode(dict(url=url))
    try:
        link = urlopen( TINYURL, data=linkdata ).read().strip()
    except URLError:
        # there was an error
        link = None
    return link

def TwitterAccounts(context):
    registry = getUtility(IRegistry)
    accounts = registry['collective.twitter.accounts']
    
    return SimpleVocabulary.fromValues(accounts.keys())


alsoProvides(TwitterAccounts, IContextSourceBinder)

class ITwitterPublishAction(Interface):
    """ Twitter Config """
    
    tw_account = schema.Choice(title=_(u'Twitter account'),
                                  description=_(u"Which twitter account to use."),
                                  required=True,
                                  source=TwitterAccounts)

#    
#    short_service_vocabulary = SimpleVocabulary(["tinyURL", "goo.gl"])
#    short_service = schema.Choice(title=_(u'URL Shortener service'),
#                                  description=_(u"Choose the service used to "
#                                                 "shorten the URL"),
#                                  required=False,
#                                  vocabulary=short_service_vocabulary)
#                         
                         

class TwitterPublishAction(SimpleItem):
    """ 
    The actual persistent implementation of the action element.
    """
    
    implements(ITwitterPublishAction, IRuleElementData)
    
    tw_account = ""   
#    short_service = ""
    element = "collective.twitter.action.TwitterPublishAction"

    @property
    def summary(self):
        return _(u"Twitter account: ${user}", mapping=dict(user=self.tw_account))


class TwitterPublishActionExecutor(object):
    """ 
    The executor for this action
    """
    implements(IExecutable)
    adapts(Interface, ITwitterPublishAction, IObjectEvent)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        context = aq_inner(self.event.object)
        ploneutils = getToolByName(self.context, 'plone_utils')
        registry = getUtility(IRegistry)
        accounts = registry['collective.twitter.accounts']
        
        account = accounts.get(self.element.tw_account, {})

        if account:
            tw =  twitter.Api(consumer_key = account.get('consumer_key'),
                              consumer_secret = account.get('consumer_secret'),
                              access_token_key = account.get('oauth_token'), 
                              access_token_secret = account.get('oauth_token_secret'),)
                              
            obj = self.event.object
            title = obj.Title()
            url = getTinyURL(obj.absolute_url())
            if url is None:
                return False
            twittertext = "%s\n%s" % ( title[0:140-(len(url)+2)], url )
    
            try:
                status = tw.PostUpdate(twittertext)
                msg = _("Item published to twitter")
            except HTTPError, e:
                msg = _("Error while publishing to twitter %s" % str(e))
            except twitter.TwitterError, e:
                msg = _("Error while publishing to twitter %s" % str(e))
                
            ploneutils.addPortalMessage( msg )
            self.context.REQUEST.response.redirect(obj.absolute_url())
            
        else:
            msg = _("Could not publish to twitter, seems the account %s "
                    "was removed from the list of authorized accounts for this "
                    "site." % self.element.tw_account)
            ploneutils.addPortalMessage( msg )
            self.context.REQUEST.response.redirect(obj.absolute_url())
 
            
        return True

class TwitterPublishActionAddForm(AddForm):
    """An add form for portal type conditions.
    """
    form_fields = form.FormFields(ITwitterPublishAction)
    label = _(u"Publish to Twitter action.")
    description = _(u"Publish a title and short URL to Twitter")
    form_name = _(u"Select account")

    def create(self, data):
        c = TwitterPublishAction()
        form.applyChanges(c, self.form_fields, data)
        return c
    
class TwitterPublishActionEditForm(EditForm):
    """An edit form for portal type conditions
    """
    form_fields = form.FormFields(ITwitterPublishAction)
    label = _(u"Edit publish to Twitter action.")
    description = _(u"Publish a title and short URL to Twitter")
    form_name = _(u"Select account")
 
