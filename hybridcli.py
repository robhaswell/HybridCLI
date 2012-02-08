#!/usr/bin/env python
import os, sys, ConfigParser

from optparse import OptionParser
from twisted.internet import reactor, defer

from txhybridcluster import utils
from adminapi import Client

site = "Default Site" # in future this will be an option

DIR = os.path.expanduser('~/.hybrid-cli')
CONFIG = DIR + '/config'

class Command(object):
    def __init__(self, domain, username, apikey):
        self.domain = domain
        self.username = username
        self.apikey = apikey


    def getApiClient(self):
        return Client(self.domain, self.username, self.apikey)



class RunCommand(Command):
    def setOptions(self, options, args):
        self.cmd = " ".join(args)
        self.params = {}
        if options.tagname:
            self.params['tagname'] = options.tagname


    def run(self):
        api = self.getApiClient()
        return api.listWebsites(**self.params).addCallback(self.gotWebsiteList).addCallback(lambda r: reactor.stop())


    def gotWebsiteList(self, response):
        from pipes import quote
        websites = response['websites']
        for website in websites:
            domain = website['name']
            print "Executing on", domain
            os.system('ssh -o "StrictHostKeyChecking no" %s@%s X_HYBRID_CLUSTER=1 %s' % (domain, self.domain, quote(self.cmd)))


commands = {
        'run': RunCommand
    }

def main():
    parser = OptionParser(usage="usage: %prog [options] COMMAND [command-options]")
    parser.add_option('--site', dest='site', default=site)
    parser.add_option('--tagname', dest='tagname', default=False)
    (options, args) = parser.parse_args()
    
    if not os.path.exists(DIR):
        os.mkdir(DIR)

    config = ConfigParser.ConfigParser()
    try:
        config.read(CONFIG)
        domain = config.get(options.site, 'domain')
        username = config.get(options.site, 'username')
        apikey = config.get(options.site, 'apikey')
    except:
        # does not exist
        print "No configuration for site '%s' yet" % (options.site,)
        try:
            config.add_section(options.site)
        except ConfigParser.DuplicateSectionError:
            pass
        domain = raw_input('Enter domain: ')
        username = raw_input('Enter username: ')
        apikey = raw_input('Enter apikey: ')

        config.set(options.site, 'domain', domain)
        config.set(options.site, 'username', username)
        config.set(options.site, 'apikey', apikey)
        with open(CONFIG, 'wb') as configfile:
            config.write(configfile)
    del config

    try:
        try:
            command = args.pop(0)
        except IndexError:
            raise UsageError('Command not specified')
        try:
            command_object = commands[command](domain, username, apikey)
            command_object.setOptions(options, args)
        except KeyError:
            raise UsageError("Unknown command '%s' %" % (command,))

        reactor.callWhenRunning(command_object.run)
        reactor.run()
    except UsageError, e:
        print e
        parser.print_help()
    
class UsageError(Exception):
    def __init__(self, message):
        self.message = message


    def __str__(self):
        return self.message


