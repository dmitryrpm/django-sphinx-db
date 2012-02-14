from django.db.models.sql import compiler

class SphinxQLCompiler(compiler.SQLCompiler):
    def get_columns(self, *args, **kwargs):
        columns = super(SphinxQLCompiler, self).get_columns(*args, **kwargs)
        for i, column in enumerate(columns):
            if '.' in column:
                columns[i] = column.partition('.')[2]
        return columns

class SQLInsertCompiler(compiler.SQLInsertCompiler, SphinxQLCompiler):
    pass

class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SphinxQLCompiler):
    pass

class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SphinxQLCompiler):
    def as_sql(self):
        qn = self.connection.ops.quote_name
        opts = self.query.model._meta
        result = ['REPLACE INTO %s' % qn(opts.db_table)]
        # This is a bit ugly, we have to scrape information from the where clause
        # and put it into the field/values list. Sphinx will not accept an UPDATE
        # statement that includes full text data, only INSERT/REPLACE INTO.
        lvalue, lookup_type, value_annot, params_or_value = self.query.where.children[0].children[0]
        (table_name, column_name, column_type), val = lvalue.process(lookup_type, params_or_value, self.connection)
        fields, values, params = [column_name], ['%s'], [val[0]]
        # Now build the rest of the fields into our query.
        for field, model, val in self.query.values:
            if hasattr(val, 'prepare_database_save'):
                val = val.prepare_database_save(field)
            else:
                val = field.get_db_prep_save(val, connection=self.connection)

            # Getting the placeholder for the field.
            if hasattr(field, 'get_placeholder'):
                placeholder = field.get_placeholder(val, self.connection)
            else:
                placeholder = '%s'

            if hasattr(val, 'evaluate'):
                val = SQLEvaluator(val, self.query, allow_joins=False)
            name = field.column
            if hasattr(val, 'as_sql'):
                sql, params = val.as_sql(qn, self.connection)
                values.append(sql)
                params.extend(params)
            elif val is not None:
                values.append(placeholder)
                params.append(val)
            else:
                values.append('NULL')
            fields.append(name)
        result.append('(%s)' % ', '.join(fields))
        result.append('VALUES (%s)' % ', '.join(values))
        return ' '.join(result), params

class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SphinxQLCompiler):
    pass

class SQLDateCompiler(compiler.SQLDateCompiler, SphinxQLCompiler):
    pass
