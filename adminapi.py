#!/usr/bin/env python
import re
from twisted.python import failure
from twisted.internet import reactor, defer, protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from urllib import urlencode

from simplejson import loads

class Client(object):
    def __init__(self, domain, username, apikey):
        self.domain = domain
        self.endpoint = "http://%s/admin_api" % (domain,)
        self.username = username
        self.apikey= apikey


    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    def decamelise(self, name):
        s1 = self.first_cap_re.sub(r'\1_\2', name)
        return self.all_cap_re.sub(r'\1_\2', s1).lower()


    def __getattr__(self, funcname):
        command = self.decamelise(funcname)
        url = self.endpoint + '/' + command
        def inner(**kw):
            query = {
                'username': self.username,
                'apikey':   self.apikey,
            }
            query.update(kw)
            postdata = urlencode(query)
            agent = Agent(reactor)

            dFinish = defer.Deferred()

            def onConnect(response):
                if not (response.code >= 200 and response.code < 300) and response.code != 302:
                    return failure.Failure(AdminApiConnectionError(response.code))
                d = defer.Deferred()
                def onDeliverBody(body):
                    dFinish.callback(loads(body))

                d.addCallback(onDeliverBody)
                response.deliverBody(SimpleReceiver(d))
                return d

            def onError(failure):
                self.printError(failure)

            d = agent.request(
                'POST',
                url,
                Headers({
                    'User-Agent': ['Hybrid Web Cluster admin api agent'],
                    'Content-Type' : ['application/x-www-form-urlencoded'],
                }),
                StringProducer(postdata))
            d.addCallback(onConnect)
            return dFinish
        return inner



class StringProducer(object):

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass



class SimpleReceiver(protocol.Protocol):
    def __init__(s, d):
        s.buf = ''; s.d = d
    def dataReceived(s, data):
        s.buf += data
    def connectionLost(s, reason):
        # TODO: test if reason is twisted.web.client.ResponseDone, if not, do an errback
        s.d.callback(s.buf)



class AdminApiConnectionError(Exception):
    def __init__(self, code):
        self.code = code


    def __str__(self):
        return "Admin API responded to connection with HTTP code %s" % (self.code,)
