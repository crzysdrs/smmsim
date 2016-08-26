from SMM import scheduler
import jsonschema

"""
Contains the SCHEMA defined for the JSON communication protocol
for the workload generation to the SMM simulator.

The general idea is that each JSON instruction is a command
with an associated timestamp. Some commands have additional
data members that need to be present. By codifying this
relationship, there isn't a need to implement special validators
in the simulator or worry about emitting invalid JSON.

Read more about the format at http://json-schema.org/.
"""

SCHEMA = {
    'oneOf': [
        {'$ref':'#/action'},
    ],
    'action': {
        'type':'object',
        'properties':{
            'action': {
                'type':'string'
            },
            'time': {
                'type':'integer',
                'minimum': 0,
            }
        },
        'required':[
            'action',
            'time'
        ],
        'oneOf': [
            {'$ref': '#/actions/endsim'},
            {'$ref': '#/actions/removecheck'},
            {'$ref': '#/actions/newcheck'},
            {'$ref': '#/actions/changevars'},
        ],
    },
    'vars':{
        'type':'object',
        'properties': {
            'taskgran':{
                'type':'integer',
                'minimum':1,
            },
            'smmpersecond':{
                'type':'integer',
                'minimum':1,
            },
            'smmoverhead':{
                'type':'integer',
                'minimum':0,
            },
            'binsize':{
                'type':'integer',
                'minimum': 1,
            },
            'cpus':{
                'type':'integer',
                'minimum':1,
            },
            'binpacker':{
                'type':'string',
                'enum':scheduler.getBinPackers().keys()
            },
            'checksplitter':{
                'type':'string'
            },
            'rantask':{
                'type':'string',
                'enum':[
                    'reschedule',
                    'discard',
                ],
            },
            'checksplitter':{
                'type':'string',
                'enum':scheduler.getCheckSplitters().keys()
            }
        },
        'additionalProperties':False,
    },
    'check' : {
        'type':'object',
        'properties':{
            'cost':{
                'type':'integer',
                'minimum':1,
            },
            'group':{
                'type':'string'
            },
            'name':{
                'type':'string',
            },
            'priority':{
                'type':'integer',
                'minimum':1,
                'maximum':20,
            },
            'misc':{
                'type':'object',
            }
        },
        'additionalProperties':False,
    },
    'shortcheck':{
        'type':'object',
        'properties':{
            'group':{
                'type':'string'
            },
            'name':{
                'type':'string',
            },
        },
        'additionalProperties':False,
    },
    'actions': {
        'endsim': {
            'type':'object',
            'properties':{
                'action':{
                    'enum':['endsim']
                }
            },
            'required':[
                'action'
            ]
        },
        'removecheck': {
            'type':'object',
            'properties':{
                'action':{
                    'enum':['removecheck']
                },
                'checks':{
                    'type':'array',
                    'minitems':1,
                    'items':{
                        'type':'object',
                        'oneOf':[{'$ref':'#/shortcheck'}],
                    },
                }
            },
            'required':[
                'action',
                'checks'
            ]
        },
        'newcheck': {
            'type':'object',
            'properties':{
                'action':{
                    'enum':['newcheck']
                },
                'checks':{
                    'type':'array',
                    'minitems':1,
                    'items':{
                        'type':'object',
                        'oneOf':[{'$ref':'#/check'}],
                    },
                }
            },
            'required':[
                'action',
                'checks',
            ]
        },
        'changevars': {
            'type':'object',
            'properties':{
                'action':{
                    'enum':['changevars']
                },
                'vars':{
                    'type':'object',
                    'oneOf':[{'$ref':'#/vars'}]
                }
            },
            'required':[
                'action',
                'vars',
            ]
        }
    }
}

def validate(e):
    """ Validate a given dict against the SMM schema """
    jsonschema.validate(e, SCHEMA)

def validatestream():
    """ Validates a stream against the SMM schema

    Useful as an entry point for a standalone Schema validator.
    """
    import sys
    import json
    import functools
    stream = sys.stdin
    chunksize = 1024
    read = functools.partial(stream.read, chunksize)
    buffer = ""
    decoder = json.JSONDecoder()
    for chunk in iter(read, ''):
        buffer += chunk
        while buffer:
            try:
                buffer = buffer.lstrip()
                obj, idx = decoder.raw_decode(buffer)
                validate(obj)
                print(json.dumps(obj))
                buffer = buffer[idx:]
            except ValueError as e:
                break
            except jsonschema.ValidationError as e:
                raise
