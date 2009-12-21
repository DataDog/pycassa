from pycasso.columnfamily import ColumnFamily

from cassandra.ttypes import NotFoundException

__all__ = ['ColumnFamilyMap']

def create_instance(cls, **kwargs):
    instance = cls()
    instance.__dict__.update(kwargs)
    return instance

def is_missing_columns(required, actual):
    for column in required:
        if column not in actual:
            return True
    return False

class ColumnFamilyMap(object):
    def __init__(self, cls, column_family, columns=None):
        """
        Construct a ObjectFamily

        Parameters
        ----------
        cls      : class
            Instances of cls are generated on get*() requests
        column_family: ColumnFamily
            The ColumnFamily to tie with cls
        columns : ['column']
            List of columns to require when getting from the Cassandra server.
            These columns are also the only ones saved when inserting.
        """
        self.cls = cls
        self.column_family = column_family
        self.columns = columns

    def get(self, key, *args, **kwargs):
        """
        Fetch a key from a Cassandra server
        
        Parameters
        ----------
        key : str
            The key to fetch
        columns : [str]
            Limit the columns fetched to the specified list
        column_start = str
            Only fetch when a column is >= column_start
        column_finish = str
            Only fetch when a column is <= column_finish
        column_reversed = bool
            Fetch the columns in reverse order. Currently this does nothing
            because columns are converted into a dict.
        column_count = int
            Limit the number of columns fetched per key
        return_timestamp = bool
            If true, return a (value, timestamp) tuple for each column

        Returns
        -------
        Class instance
        """
        kwargs['columns'] = self.columns
        columns = self.column_family.get(key, *args, **kwargs)
        if self.columns is not None and is_missing_columns(self.columns, columns):
            raise NotFoundException
        return create_instance(self.cls, key=key, **columns)

    def multiget(self, *args, **kwargs):
        """
        Fetch multiple key from a Cassandra server
        
        Parameters
        ----------
        keys : [str]
            A list of keys to fetch
        columns : [str]
            Limit the columns fetched to the specified list
        column_start = str
            Only fetch when a column is >= column_start
        column_finish = str
            Only fetch when a column is <= column_finish
        column_reversed = bool
            Fetch the columns in reverse order. Currently this does nothing
            because columns are converted into a dict.
        column_count = int
            Limit the number of columns fetched per key
        return_timestamp = bool
            If true, return a (value, timestamp) tuple for each column

        Returns
        -------
        {'key': Class instance} 
        """
        kwargs['columns'] = self.columns
        kcmap = self.column_family.multiget(*args, **kwargs)
        ret = {}
        for key, columns in kcmap.iteritems():
            if self.columns is not None and is_missing_columns(self.columns, columns):
                break
            ret[key] = create_instance(self.cls, key=key, **columns)
        return ret

    def get_count(self, *args, **kwargs):
        """
        Count the number of columns for a key

        Parameters
        ----------
        key : str
            The key with which to count columns

        Returns
        -------
        int Count of columns
        """
        return self.column_family.get_count(*args, **kwargs)

    def iter_get_range(self, *args, **kwargs):
        """
        Get an iterator over keys in a specified range
        
        Parameters
        ----------
        start : str
            Start from this key (inclusive)
        finish : str
            End at this key (inclusive)
        columns : [str]
            Limit the columns fetched to the specified list
        column_start = str
            Only fetch when a column is >= column_start
        column_finish = str
            Only fetch when a column is <= column_finish
        column_reversed = bool
            Fetch the columns in reverse order. Currently this does nothing
            because columns are converted into a dict.
        column_count = int
            Limit the number of columns fetched per key
        row_count = int
            Limit the number of rows fetched
        return_timestamp = bool
            If true, return a (value, timestamp) tuple for each column

        Returns
        -------
        iterator over Class instance
        """
        kwargs['columns'] = self.columns
        for key, columns in self.column_family.iter_get_range(*args, **kwargs):
            if self.columns is not None and is_missing_columns(self.columns, columns):
                continue
            yield create_instance(self.cls, key=key, **columns)

    def get_range(self, *args, **kwargs):
        """
        Get a list of keys in a specified range
        
        Parameters
        ----------
        start : str
            Start from this key (inclusive)
        finish : str
            End at this key (inclusive)
        columns : [str]
            Limit the columns fetched to the specified list
        column_start = str
            Only fetch when a column is >= column_start
        column_finish = str
            Only fetch when a column is <= column_finish
        column_reversed = bool
            Fetch the columns in reverse order. Currently this does nothing
            because columns are converted into a dict.
        column_count = int
            Limit the number of columns fetched per key
        row_count = int
            Limit the number of rows fetched
        return_timestamp = bool
            If true, return a (value, timestamp) tuple for each column

        Returns
        -------
        list of Class instance
        """
        return [instance for instance in self.iter_get_range(*args, **kwargs)]

    def insert(self, instance, columns=None):
        """
        Insert or update columns for a key

        Parameters
        ----------
        instance : Class instance
            The key to insert or update the columns at
        columns : ['column']
            Limit the columns inserted to this list

        Returns
        -------
        int timestamp
        """
        insert_dict = {}
        columns = columns or self.columns
        if columns is not None:
            for column in columns:
                insert_dict[column] = getattr(instance, column)
        else:
            for key, value in instance.__dict__.iteritems():
                if key != 'key':
                    insert_dict[key] = value
        return self.column_family.insert(instance.key, insert_dict)

    def remove(self, instance, columns=None):
        """
        Remove this instance

        Parameters
        ----------
        instance : Class instance
            Remove the instance where the key is instance.key
        columns : ['column']
            Limit the columns removed to this list

        Returns
        -------
        int timestamp
        """
        # Hmm, should we only remove the columns specified on construction?
        # It's slower, so we'll leave it out.
        # columns = columns or self.columns
        if columns is None:
            return self.column_family.remove(instance.key)
        timestamp = None
        for column in columns:
            timestamp = self.column_family.remove(instance.key, column)
        return timestamp