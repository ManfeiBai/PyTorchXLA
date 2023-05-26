import torch_xla


class TfRecordReader(object):
  """Reads TfRecords or TfExamples.

  Args:
    path (string): The path to the file containing TfRecords.
    compression (string, optional): The compression type. The empty string for
      no compression, otherwise ``ZLIB`` or ``GZIP``.
      Default: No compression.
    buffer_size (int, optional): The size of the buffer to be used to read
      TfRecords.
      Default: 16 * 1024 * 1024
    transforms (dict, optional): A dictionary with the key matching the
      TfExample label name, and value which is either a callable which will be
      called to tranform the matching tensor data, or ``STR`` for string
      conversion.
  """

  def __init__(self,
               path,
               compression='',
               buffer_size=16 * 1024 * 1024,
               transforms=None):
    self._reader = torch_xla._XLAC._xla_create_tfrecord_reader(
        path, compression=compression, buffer_size=buffer_size)
    self._transforms = transforms

  def read_record(self):
    """Reads a TfRecord and returns the raw bytes.

    Returns:
      The raw bytes of the record, or ``None`` in case of EOF.
    """
    return torch_xla._XLAC._xla_tfrecord_read(self._reader)
