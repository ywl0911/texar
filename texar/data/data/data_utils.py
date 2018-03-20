#
"""
Various utilities specific to data processing.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six

import tensorflow as tf

import numpy as np

from texar.core import utils

# pylint: disable=invalid-name

__all__ = [
    "_DataSpec",
    "maybe_tuple",
    "make_partial",
    "make_chained_transformation",
    "make_combined_transformation",
    "random_shard_dataset",
    "count_file_lines"
]


#TODO(zhiting): unit test
class _DataSpec(object): # pylint: disable=too-few-public-methods
    """Dataset specification. Used to pass necessary info to
    user-defined tranformation functions.

    Args:
        dataset: Instance of :tf_main:`tf.data.Dataset <data/Dataset>`.
        dataset_size (int): Number of data samples.
        decoder: A (list of) data decoder.
        vocab: A (list of) :class:`texar.data.Vocab` instance.
        embeddidng: A (list of) :class:`texar.data.Embedding` instance.
        **kwargs: Any remaining dataset-specific fields.
    """
    # pylint: disable=too-many-arguments
    def __init__(self, dataset=None, dataset_size=None, decoder=None,
                 vocab=None, embedding=None, **kwargs):
        kwargs['dataset'] = dataset
        kwargs['dataset_size'] = dataset_size
        kwargs['decoder'] = decoder
        kwargs['vocab'] = vocab
        kwargs['embedding'] = embedding
        self.__dict__.update(kwargs)


    def add_spec(self, **kwargs):
        """Adds new field.
        """
        self.__dict__.update(kwargs)

    def get_ith_data_spec(self, i):
        """Returns an instance of :class:`DataSpec` that contains the
        :attr:`i`-th specifications.
        """
        kwargs = {}
        for k, v in six.iteritems(self.__dict__):
            kwargs[k] = v[i] if isinstance(v, (tuple, list)) else v
        return _DataSpec(**kwargs)

    def set_ith_data_spec(self, i, data_spec, num):
        """Sets the i-th specification to respective values in
        :attr:`data_spec`.
        """
        for k, v in six.iteritems(data_spec.__dict__):
            if k in self.__dict__:
                v_ = self.__dict__[k]
                if isinstance(v_, (tuple, list)):
                    v_[i] = v
                else:
                    self.__dict__[k] = v
            else:
                v_ = [None] * num
                v_[i] = v
                self.__dict__[k] = v_


def maybe_tuple(data):
    """Returns `tuple(data)` if :attr:`data` contains more than 1 elements.

    Used to wrap `map_func` inputs.
    """
    data = tuple(data)
    data = data if len(data) > 1 else data[0]
    return data

def make_partial(fn, *args, **kwargs):
    """Returns a new function with single argument by freezing other arguments
    of :attr:`fn`.
    """
    def _new_fn(data):
        return fn(data, *args, **kwargs)
    return _new_fn

def make_chained_transformation(tran_fns, *args, **kwargs):
    """Returns a dataset transformation function that applies a list of
    transformations sequentially.

    Args:
        tran_fns (list): A list of dataset transformation.
        *args: Extra arguments for each of the transformation function.
        **kwargs: Extra keyword arguments for each of the transformation
            function.

    Returns:
        A transformation function to be used in
        :tf_main:`tf.data.Dataset.map <data/Dataset#map>`.
    """
    def _chained_fn(data):
        for tran_fns_i in tran_fns:
            data = tran_fns_i(data, *args, **kwargs)
        return data

    return _chained_fn

def make_combined_transformation(tran_fns, name_prefix=None, *args, **kwargs):
    """Returns a dataset transformation function that applies
    transformations to each component of the data.

    The data to be transformed must be a tuple of the same length
    of :attr:`tran_fns`.

    Args:
        tran_fns (list): A list of elements where each element is a
            transformation function or a list of transformation functions.
        name_prefix (list, optional): Prefix to the field names of each
            component of the data, to prevent fields with the same name
            in different components from overriding each other. If not `None`,
            must be of the same length of :attr:`tran_fns`.
        *args: Extra arguments for each of the transformation function.
        **kwargs: Extra keyword arguments for each of the transformation
            function.

    Returns:
        A transformation function to be used in
        :tf_main:`tf.data.Dataset.map <data/Dataset#map>`.
    """
    if name_prefix and len(name_prefix) != len(tran_fns):
        raise ValueError("`name_prefix`, if provided, must be of the same "
                         "length of `tran_fns`.")

    def _combined_fn(data):
        transformed_data = {}
        for i, tran_fns_i in enumerate(tran_fns):
            data_i = data[i]
            # Process data_i
            if not isinstance(tran_fns_i, (list, tuple)):
                tran_fns_i = [tran_fns_i]
            for tran_fns_ij in tran_fns_i:
                data_i = tran_fns_ij(data_i, *args, **kwargs)
            # Add to dict by appending name prefix
            for name, value in six.iteritems(data_i):
                new_name = name
                if name_prefix:
                    new_name = "{}_{}".format(name_prefix[i], name)
                if new_name in transformed_data:
                    raise ValueError(
                        "Field name already exists: {}".format(new_name))
                transformed_data[new_name] = value
        return transformed_data

    return _combined_fn

def random_shard_dataset(dataset_size, shard_size, seed=None):
    """Returns a dataset transformation function that randomly shards a
    dataset.
    """
    num_shards = utils.ceildiv(dataset_size, shard_size)
    boundaries = np.linspace(0, dataset_size, num=num_shards, endpoint=False,
                             dtype=np.int64) #pylint: disable=no-member

    def _shard_fn(dataset):
        sharded_dataset = (
            tf.data.Dataset.from_tensor_slices(boundaries)
            .shuffle(num_shards, seed=seed)
            .flat_map(lambda lb: dataset.skip(lb).take(shard_size)))
        return sharded_dataset

    return _shard_fn

def count_file_lines(filenames):
    """Counts the number of lines in the file(s).
    """
    def _count_lines(fn):
        with open(fn) as f:
            i = -1
            for i, _ in enumerate(f):
                pass
            return i + 1

    if not isinstance(filenames, (list, tuple)):
        filenames = [filenames]
    num_lines = np.sum([_count_lines(fn) for fn in filenames])
    return num_lines



