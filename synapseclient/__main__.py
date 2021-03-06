"""
***************************
Synapse command line client
***************************

For help, type synapse -h.

"""

import argparse
import os
import shutil
import sys
import synapseclient
from synapseclient import Activity
import utils
import signal
import json


def query(args, syn):
    """TODO_Sphinx."""
    
    ## TODO: Should use loop over multiple returned values if return is too long
    results = syn.chunkedQuery(' '.join(args.queryString))

    headings = {}
    temp = [] # Since query returns a generator, the results must be stored locally
    for res in results:
        temp.append(res)
        for head in res:
            headings[head] = True
    if len(headings) == 0: # No results found
        return 
    print '\t'.join(headings)
    
    for res in temp:
        out = []
        for key in headings:
            out.append(str(res.get(key, "")))
        print "\t".join(out)

        
def get(args, syn):
    """TODO_Sphinx."""
    
    entity = syn.get(args.id)
    
    ## TODO: Is this part even necessary?
    ## (Other than the print statements)
    if 'files' in entity:
        for file in entity['files']:
            src = os.path.join(entity['cacheDir'], file)
            dst = os.path.join('.', file.replace(".R_OBJECTS/",""))
            print 'creating %s' % dst
            if not os.path.exists(os.path.dirname(dst)):
                os.mkdir(dst)
            shutil.copyfile(src, dst)
    else:
        sys.stderr.write('WARNING: No files associated with entity %s\n' % (args.id,))
        syn.printEntity(entity)
    return entity
    
    
def store(args, syn):
    """TODO_Sphinx."""
    
    # Concatenate the multi-part arguments "name" and "description" 
    # so that the other functions can accept them
    if args.name is not None: args.name = ' '.join(args.name)
    if args.description is not None: args.description = ' '.join(args.description)
    
    # --id indicates intention to update()
    if args.id is not None:
        if args.file is not None:
            update(args, syn)
        else:
            print 'Update requires --file'
        return
        
    # --file, --used, and --executed indicates intention to upload()
    if args.file is not None or args.used is not None or args.executed is not None:
        if args.parentid is not None:
            upload(args, syn)
        else: 
            print 'Add requires --parentid'
        return
       
    # --name indicates intention to create()
    if args.name is not None:
        if args.type is not None:
            create(args, syn)
        else:
            print 'Create requires --type'
        return
        
    print 'Could not interpret arguments.  Try using synapse create, add, or update.'


def cat(args, syn):
    """TODO_Sphinx."""
    
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    entity = syn.get(args.id)
    if 'files' in entity:
        for file in entity['files']:
            with open(os.path.join(entity['cacheDir'], file)) as input:
                for line in input:
                    print line

                    
def show(args, syn):
    """Show metadata for an entity."""
    ent = syn.get(args.id, downloadFile=False)
    syn.printEntity(ent)

    
def delete(args, syn):
    """TODO_Sphinx."""
    
    syn.delete(args.id)
    print 'Deleted entity: %s' % args.id

    
def upload(args, syn):
    """TODO_Sphinx."""
    
    if args.type == 'File': args.type = 'FileEntity'
    entity = {'name': args.name,
              'parentId': args.parentid,
              'description':args.description,
              'concreteType': u'org.sagebionetworks.repo.model.%s' % args.type, 
              'path': args.file}
    if utils.is_url(args.file):
        entity['synapseStore'] = False

    entity = syn.store(entity, used=args.used, executed=args.executed)

    print 'Created entity: %s\t%s from file: %s' %(entity['id'], entity['name'], args.file)
    return(entity)


def create(args, syn):
    """TODO_Sphinx."""
    
    if args.type == 'File': args.type = 'FileEntity'
    entity={'name': args.name,
            'parentId': args.parentid,
            'description':args.description,
            'concreteType': u'org.sagebionetworks.repo.model.%s' %args.type}
    entity=syn.createEntity(entity)
    print 'Created entity: %s\t%s\n' %(entity['id'],entity['name'])
    return(entity)


def update(args, syn):
    """TODO_Sphinx."""
    
    entity = syn.get(args.id)
    entity.path = args.file
    entity = syn.store(entity)
    print 'Updated entity: %s\t%s from file: %s\n' %(entity['id'],entity['name'], args.file)


def onweb(args, syn):
    """TODO_Sphinx."""
    
    syn.onweb(args.id)

def setProvenance(args, syn):
    """Set provenance information on a synapse entity."""
    
    activity = Activity(name=args.name, description=args.description)
    if args.used:
        for item in args.used:
            activity.used(item)
    if args.executed:
        for item in args.executed:
            activity.used(item, wasExecuted=True)
    activity = syn.setProvenance(args.id, activity)

    # Display the activity record, if -o or -output specified
    if args.output:
        if args.output=='STDOUT':
            sys.stdout.write(json.dumps(activity))
            sys.stdout.write('\n')
        else:
            with open(args.output, 'w') as f:
                f.write(json.dumps(activity))
                f.write('\n')
    else:
        print 'Set provenance record %s on entity %s\n' % (str(activity['id']), str(args.id))


def getProvenance(args, syn):
    """TODO_Sphinx."""
    
    activity = syn.getProvenance(args.id)

    if args.output is None or args.output=='STDOUT':
        print json.dumps(activity)
    else:
        with open(args.output, 'w') as f:
            f.write(json.dumps(activity))
            f.write('\n')
    
    
def submit(args, syn):
    """TODO_Sphinx."""
    
    if args.name is not None: args.name = ' '.join(args.name)
    
    submission = syn.submit(args.evaluation, args.entity, name=args.name, teamName=args.teamName)
    print 'Submitted (id: %s) entity: %s\t%s to Evaluation: %s\n' %(submission['id'], submission['entityId'], submission['name'], submission['evaluationId'])


def main():
    parser = argparse.ArgumentParser(description='Interfaces with the Synapse repository.')
    parser.add_argument('--version', action='version', version='Synapse Client %s' % synapseclient.__version__)
    parser.add_argument('-u', '--username', dest='synapseUser', help='Username used to connect to Synapse')
    parser.add_argument('-p', '--password', dest='synapsePassword', help='Password used to connect to Synapse')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--skip-checks', '-s', dest='skip_checks', action='store_true', help='suppress checking for version upgrade messages and endpoint redirection')


    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands',
                                       help='additional help')


    #parser_login = subparsers.add_parser('login', help='login to Synapse')
    #parser_login.add_argument('synapseUser', metavar='USER', type=str, help='Synapse username')
    #parser_login.add_argument('synapsePassword', metavar='PASSWORD', type=str, help='Synapse password')

    
    parser_query = subparsers.add_parser('query', help='Performs SQL like queries on Synapse')
    parser_query.add_argument('queryString', metavar='string', type=str, nargs='*',
                         help='A query string, see https://sagebionetworks.jira.com/wiki/display/PLFM/Repository+Service+API#RepositoryServiceAPI-QueryAPI for more information')
    parser_query.set_defaults(func=query)

    parser_get = subparsers.add_parser('get', help='downloads a dataset from Synapse')
    parser_get.add_argument('id', metavar='syn123', type=str, 
                         help='Synapse ID of form syn123 of desired data object')
    parser_get.set_defaults(func=get)

    parser_store = subparsers.add_parser('store', help='depending on the arguments supplied, store will either create, add, or update')
    group = parser_store.add_mutually_exclusive_group()
    group.add_argument('--id', metavar='syn123', type=str, 
                         help='Synapse ID of form syn123 of the Synapse object to update')
    group.add_argument('--parentid', metavar='syn123', type=str,  
                         help='Synapse ID of project or folder where to upload new data.')
    parser_store.add_argument('--name', type=str, nargs="+", 
                         help='Name of data object in Synapse')
    parser_store.add_argument('--description', type=str, nargs="+", 
                         help='Description of data object in Synapse.')
    parser_store.add_argument('--type', type=str, default='File',
                         help='Type of object, such as "File", "Folder", or "Project", to create in Synapse. Defaults to "File"')
    parser_store.add_argument('--used', metavar='TargetID', type=str, nargs='*',
                         help='ID of a target data entity from which the specified entity is derived')
    parser_store.add_argument('--executed', metavar='TargetID', type=str, nargs='*',
                         help='ID of a code entity from which the specified entity is derived')
    parser_store.add_argument('--file', type=str,
                         help='file to be added to synapse.')
    parser_store.set_defaults(func=store)
    
    parser_submit = subparsers.add_parser('submit', help='submit an entity for evaluation')
    parser_submit.add_argument('--evaluation', type=str, required=True, 
                         help='Evaluation ID where the entity will be submitted')
    parser_submit.add_argument('--entity', type=str, required=True, 
                         help='Synapse ID of the entity to be submitted')
    parser_submit.add_argument('--name', type=str, nargs="+", 
                         help='Name of the submission')
    parser_submit.add_argument('--teamName', '--team', type=str,
                         help='Publicly displayed name of team for the submission')
    parser_submit.set_defaults(func=submit)

    parser_get = subparsers.add_parser('show', help='show metadata for an entity')
    parser_get.add_argument('id', metavar='syn123', type=str, 
                         help='Synapse ID of form syn123 of desired synapse object')
    parser_get.set_defaults(func=show)

    parser_cat = subparsers.add_parser('cat', help='prints a dataset from Synapse')
    parser_cat.add_argument('id', metavar='syn123', type=str,
                         help='Synapse ID of form syn123 of desired data object')
    parser_cat.set_defaults(func=cat)

    parser_add = subparsers.add_parser('add', help='uploads and adds a dataset to Synapse')
    parser_add.add_argument('-parentid', '-parentId', metavar='syn123', type=str, required=True, 
                         help='Synapse ID of project or folder where to upload data.')
    #TODO make so names can have white space
    parser_add.add_argument('-name', metavar='NAME', type=str, required=False,
                         help='Name of data object in Synapse')
    #TODO make sure that description can have whitespace
    parser_add.add_argument('-description', metavar='DESCRIPTION', type=str, 
                         help='Description of data object in Synapse.')
    parser_add.add_argument('-type', type=str, default='File',
                         help='Type of object to create in synapse. Defaults to "File". Deprecated object types include "Data" and "Code".')
    parser_add.add_argument('-used', metavar='TargetID', type=str, nargs='*',
                         help='ID of a target data entity from which the specified entity is derived')
    parser_add.add_argument('-executed', metavar='TargetID', type=str, nargs='*',
                         help='ID of a code entity from which the specified entity is derived')
    parser_add.add_argument('file', type=str,
                         help='file to be added to synapse.')
    parser_add.set_defaults(func=upload)


    parser_set_provenance = subparsers.add_parser('set-provenance', help='create provenance records')
    parser_set_provenance.add_argument('-id', metavar='syn123', type=str, required=True,
                         help='Synapse ID of entity whose provenance we are accessing.')
    parser_set_provenance.add_argument('-name', metavar='NAME', type=str, required=False,
                         help='Name of the activity that generated the entity')
    parser_set_provenance.add_argument('-description', metavar='DESCRIPTION', type=str, required=False, 
                         help='Description of the activity that generated the entity')
    parser_set_provenance.add_argument('-o', '-output', metavar='OUTPUT_FILE', dest='output',
                         const='STDOUT', nargs='?', type=str,
                         help='Output the provenance record in JSON format')
    parser_set_provenance.add_argument('-used', metavar='TargetID', type=str, nargs='*',
                         help='ID of a target data entity from which the specified entity is derived')
    parser_set_provenance.add_argument('-executed', metavar='TargetID', type=str, nargs='*',
                         help='ID of a code entity from which the specified entity is derived')
    parser_set_provenance.set_defaults(func=setProvenance)


    parser_get_provenance = subparsers.add_parser('get-provenance', help='show provenance records')
    parser_get_provenance.add_argument('-id', metavar='syn123', type=str, required=True,
                         help='Synapse ID of entity whose provenance we are accessing.')
    parser_get_provenance.add_argument('-o', '-output', metavar='OUTPUT_FILE', dest='output',
                         const='STDOUT', nargs='?', type=str,
                         help='Output the provenance record in JSON format')
    parser_get_provenance.set_defaults(func=getProvenance)


    parser_create = subparsers.add_parser('create', help='Creates folders or projects on Synapse')
    parser_create.add_argument('-parentid', '-parentId', metavar='syn123', type=str, required=False, 
                         help='Synapse ID of project or folder where to place folder [not used with project]')
    #TODO make so names can have white space
    parser_create.add_argument('-name', metavar='NAME', type=str, required=True,
                         help='Name of folder/project.')
    #TODO make sure that description can have whitespace
    parser_create.add_argument('-description', metavar='DESCRIPTION', type=str, 
                         help='Description of project/folder')
    parser_create.add_argument('type', type=str,
                         help='Type of object to create in synapse one of {Project, Folder}')
    parser_create.set_defaults(func=create)


    parser_update = subparsers.add_parser('update', help='uploads a new file to an existing Synapse Entity')
    parser_update.add_argument('-id', metavar='syn123', type=str, required=True,
                         help='Synapse ID of entity to be updated')
    parser_update.add_argument('file', type=str,
                         help='file to be added to synapse.')
    parser_update.set_defaults(func=update)

    parser_delete = subparsers.add_parser('delete', help='removes a dataset from Synapse')
    parser_delete.add_argument('id', metavar='syn123', type=str,
                         help='Synapse ID of form syn123 of desired data object')
    parser_delete.set_defaults(func=delete)


    parser_onweb = subparsers.add_parser('onweb', help='opens Synapse website for Entity')
    parser_onweb.add_argument('id', type=str,
                         help='Synapse id')
    parser_onweb.set_defaults(func=onweb)

    args = parser.parse_args()

    #TODO Perform proper login either prompt for info or use parameters
    ## if synapseUser and synapsePassword are not given, try to use cached session token
    syn = synapseclient.Synapse(debug=args.debug, skip_checks=args.skip_checks)
    syn.login(args.synapseUser, args.synapsePassword, silent=True)

    #Perform the requested action
    if 'func' in args:
        try:
            args.func(args, syn)
        except Exception as ex:
            sys.stderr.write(utils.synapse_error_msg(ex))

            if args.debug:
                raise



## call main method if this file is run as a script
if __name__ == "__main__":
    main()

