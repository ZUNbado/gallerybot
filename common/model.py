from flask import current_app
from tinydb import TinyDB, where
from tinydb.operations import delete
from .tinydbs3 import S3Storage
import os
import copy

class Field(object):
    def __init__(self, value = None, type = str, default = None, required = False, primary = False, hidden = False):
        self.type = type
        self.default = default
        self.required = required
        self.value = value
        self.hidden = hidden
    
    def validate(self):
        valid = False
        if hasattr(self, 'value'):
            if self.required: valid = True
            try:
                self.value = getattr(self, 'type')(self.value)
                valid = True
            except:
                valid = False
        return valid

    def __str__(self): return u'%s' % self.value
    def __unicode__(self): return u'%s' % self.value
    def __repr__(self): return '<Attribute Value: %s>' % self.value

class Model(object):
    table = 'default'
    _exclude_fields = [ 'db', 'table', 'submit', '_exclude_fields', 'exclude_fields', '_deleted_args' ]
    _deleted_args = list()

    def __init__(self, **kwargs):
        table = os.path.join(current_app.config.get('DB_PATH', 'gallery_db'), '%s.json' % self.table)
        self.db = TinyDB(table, storage = S3Storage)
        self.eid = Field(type = int, required = False, primary = False)

        exclude_fields = getattr(self, 'exclude_fields', None)
        if exclude_fields:
            self._exclude_fields += exclude_fields

        for key, value in kwargs.items():
            if key == '_deleted_args':
                self._deleted_args = value 

            if key not in self._exclude_fields:
                self.setattr(key, value)

    def all(self):
        rows = list()
        for row in self.db.all():
            rows.append( self.as_obj(row) )
        return rows

    def filter(self, **kwargs):
        rows = list()
        eids = list()
        for field, value in kwargs.iteritems():
            if type(value) != Field:
                value = self.setattr(field, value)
            if value.validate():
                founds = self.db.search(where(field) == value.value)
                for found in founds if founds else []:
                    if found.eid not in eids:
                        eids.append(found.eid)
                        rows.append( self.as_obj(found) )
        return rows

    def get(self, eid):
        row = self.db.get(eid = eid)
        if row:
            return self.as_obj(row)
        return False

    def search(self, **kwargs):
        for field, value in kwargs.iteritems():
            if type(value) != Field:
                value = self.setattr(field, value)
            if value.validate():
                row = self.db.search(where(field) == value.value)
                if row:
                    if type(row) == list:
                        row = row[0]
                    return self.as_obj(row)
        return False

    def create(self):
        insert = self.as_dict()
        return self.db.insert(insert)

    def update(self):
        update = self.as_dict()
        for arg in self._deleted_args:
            try:
                self.db.update(delete(arg), eids = [ self.eid.value ])
            except:
                pass
        return self.db.update(update, eids = [ self.eid.value ])

    def save(self):
        if self.eid.value:
            self.eid.validate()
            return self.update()
        else:
            create = self.create()
            self.eid.value = create
            return self

    def delete(self):
        self.db.remove( eids = [ self.eid.value ] )

    def as_dict(self):
        args = dict()
        for key in self.__dict__.keys():
            if key not in self._exclude_fields:
                attr = getattr(self, key, None)
                if attr:
                    if attr.validate():
                        args[key] = attr.value
        return args

    def clean(self):
        for key in self.__dict__.keys():
            if key not in self._exclude_fields:
                delattr(self, key)

    def as_obj(self, row):
        self.clean()
        if not getattr(self, 'eid', None):
            self.eid = Field(value = row.eid, type = int, required = False, primary = False)
        for key, value in row.items():
            self.setattr(key, value)
        return copy.copy( self )

    def setattr(self, key, value):
        attr = getattr(self, key, Field())
        if type(attr) != Field:
            attr = Field()
        attr.value = value
        if key not in self._exclude_fields:
            setattr(self, key, attr)
            return attr
        if key == '_deleted_args':
            self._deleted_args.append(value)
        return False

    def from_form(self, form):
        for key, value in form.items():
            self.setattr(key, value)
        return self

    def as_form(self):
        fields = dict()
        for key in self.__dict__.keys():
            if key not in self._exclude_fields:
                attr = getattr(self, key, None)
                if attr and type(attr) == Field:
                    fields[key] = attr
        return fields

    def __repr__(self):
        if self.eid:
            return '<%s: %s>' % (self.__class__.__name__, self.eid.value)
        else:
            return '<%s>' % (self.__class__.__name__)
