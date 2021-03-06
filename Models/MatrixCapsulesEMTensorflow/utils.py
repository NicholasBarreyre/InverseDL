import os
import scipy
import numpy as np
import tensorflow as tf

from Models.MatrixCapsulesEMTensorflow.config import cfg
import Models.MatrixCapsulesEMTensorflow.data.smallNORB as norb
from keras.datasets import cifar10, cifar100
from keras import backend as K

from data_import.quick_data_load import get_examples_labels_from_directory

import logging
import daiquiri

daiquiri.setup(level=logging.DEBUG)
logger = daiquiri.getLogger(__name__)

def create_inputs_generated_with_pose_matrix(train, epochs : int, dim=32,
                                             grayscale=False,
                                             processed_dir='Models/MatrixCapsulesEMTensorflow/data/generated/translation',):
    """
    Fairly large code duplication from create_inputs_generated
    
    Basically copying over smallNORB's read_norb_tfrecord but using our
    tfrecord
    """
    
    filenames = []
    
    # TODO: Train vs Test datasets
    # This code is somewhat copied from create_inputs_norbs
    if train:
        prefix = "train"
    else:
        prefix = "test"
    
    filenames = [os.path.join(processed_dir, fname) for fname in os.listdir(processed_dir) if fname.startswith(prefix)]
        
    # Create the file queue
    filename_queue = tf.train.string_input_producer(filenames, num_epochs=epochs)
    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(filename_queue)
    
    # Parse single example
    features = tf.parse_single_example(serialized_example,
                                   features={
                                       'example': tf.FixedLenFeature([], tf.string),
                                       'label': tf.FixedLenFeature([], tf.int64),
                                       'pose': tf.FixedLenFeature([16], tf.float32)
                                   })
    
    # Decode
    img = tf.image.decode_png(features['example'], 3)
    
    # Reshape, cast
    img = tf.reshape(img, [dim, dim, 3])
    
    # Convert to grayscale if neccessary
    if grayscale:
        img = tf.image.rgb_to_grayscale(img)
    
    img = tf.cast(img, tf.float32)
    
    # Label cast
    label = features['label']
    label = tf.cast(label, tf.int32)
    
    # The pose matrix
    pose = features["pose"]
    pose = tf.cast(pose, tf.float32)
    pose = tf.reshape(pose, [16])
    
    x, y, z = tf.train.shuffle_batch([img, label, pose], num_threads=cfg.num_threads, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                              min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)
    
    return x, y, z

def create_inputs_generated(train, epochs : int, dim=32, grayscale=False, processed_dir='Models/MatrixCapsulesEMTensorflow/data/generated/translation'):
    """
    
    
    Basically copying over smallNORB's read_norb_tfrecord but using our
    tfrecord
    """
    
    filenames = []
    
    # TODO: Train vs Test datasets
    # This code is somewhat copied from create_inputs_norbs
    if train:
        prefix = "train"
    else:
        prefix = "test"
    
    filenames = [os.path.join(processed_dir, fname) for fname in os.listdir(processed_dir) if fname.startswith(prefix)]
        
    # Create the file queue
    filename_queue = tf.train.string_input_producer(filenames, num_epochs=epochs)
    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(filename_queue)
    
    # Parse single example
    features = tf.parse_single_example(serialized_example,
                                   features={
                                       'example': tf.FixedLenFeature([], tf.string),
                                       'label': tf.FixedLenFeature([], tf.int64)
                                   })
    
    # Decode
    img = tf.image.decode_png(features['example'], 3)
    
    # Reshape, cast
    img = tf.reshape(img, [dim, dim, 3])
    
    # Convert to grayscale if neccessary
    if grayscale:
        img = tf.image.rgb_to_grayscale(img)
    
    img = tf.cast(img, tf.float32)
    
    # Label cast
    label = features['label']
    label = tf.cast(label, tf.int32)
    
    x, y = tf.train.shuffle_batch([img, label], num_threads=cfg.num_threads, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)
    
    return x, y

def create_inputs_norb(is_train: bool, epochs: int):

    import re
    if is_train:
        CHUNK_RE = re.compile(r"train\d+\.tfrecords")
    else:
        CHUNK_RE = re.compile(r"test\d+\.tfrecords")

    processed_dir = 'Models/MatrixCapsulesEMTensorflow/data'
    chunk_files = [os.path.join(processed_dir, fname)
                   for fname in os.listdir(processed_dir)
                   if CHUNK_RE.match(fname)]

    image, label = norb.read_norb_tfrecord(chunk_files, epochs)

    if is_train:
        # TODO: is it the right order: add noise, resize, then corp?
        image = tf.image.random_brightness(image, max_delta=32. / 255.)
        image = tf.image.random_contrast(image, lower=0.5, upper=1.5)

        image = tf.image.resize_images(image, [48, 48])
        image = tf.random_crop(image, [32, 32, 1])
    else:
        image = tf.image.resize_images(image, [48, 48])
        image = tf.slice(image, [8, 8, 0], [32, 32, 1])

    x, y = tf.train.shuffle_batch([image, label], num_threads=cfg.num_threads, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)

    return x, y


def create_inputs_mnist(is_train):
    tr_x, tr_y = load_mnist(cfg.dataset, is_train)
    data_queue = tf.train.slice_input_producer([tr_x, tr_y], capacity=64 * 8)
    x, y = tf.train.shuffle_batch(data_queue, num_threads=8, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)

    return (x, y)


def create_inputs_fashion_mnist(is_train):
    tr_x, tr_y = load_mnist(cfg.dataset_fashion_mnist, is_train)
    data_queue = tf.train.slice_input_producer([tr_x, tr_y], capacity=64 * 8)
    x, y = tf.train.shuffle_batch(data_queue, num_threads=8, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)

    return (x, y)


def load_mnist(path, is_training):
    fd = open(os.path.join(cfg.dataset, 'train-images-idx3-ubyte'))
    loaded = np.fromfile(file=fd, dtype=np.uint8)
    trX = loaded[16:].reshape((60000, 28, 28, 1)).astype(np.float32)

    fd = open(os.path.join(cfg.dataset, 'train-labels-idx1-ubyte'))
    loaded = np.fromfile(file=fd, dtype=np.uint8)
    trY = loaded[8:].reshape((60000)).astype(np.int32)

    fd = open(os.path.join(cfg.dataset, 't10k-images-idx3-ubyte'))
    loaded = np.fromfile(file=fd, dtype=np.uint8)
    teX = loaded[16:].reshape((10000, 28, 28, 1)).astype(np.float32)

    fd = open(os.path.join(cfg.dataset, 't10k-labels-idx1-ubyte'))
    loaded = np.fromfile(file=fd, dtype=np.uint8)
    teY = loaded[8:].reshape((10000)).astype(np.int32)

    # normalization and convert to a tensor [60000, 28, 28, 1]
    # trX = tf.convert_to_tensor(trX, tf.float32)
    # teX = tf.convert_to_tensor(teX, tf.float32)

    # => [num_samples, 10]
    # trY = tf.one_hot(trY, depth=10, axis=1, dtype=tf.float32)
    # teY = tf.one_hot(teY, depth=10, axis=1, dtype=tf.float32)

    if is_training:
        return trX, trY
    else:
        return teX, teY


def create_inputs_cifar10(is_train):
    tr_x, tr_y = load_cifar10(is_train)
    data_queue = tf.train.slice_input_producer([tr_x, tr_y], capacity=64 * 8)
    x, y = tf.train.shuffle_batch(data_queue, num_threads=8, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)

    return (x, y)


def load_cifar10(is_training):
    # https://keras.io/datasets/
    assert(K.image_data_format() == 'channels_last')
    if is_training:
        return cifar10.load_data()[0]
    else:
        return cifar10.load_data()[1]


def create_inputs_cifar100(is_train):
    tr_x, tr_y = load_cifar100(is_train)
    data_queue = tf.train.slice_input_producer([tr_x, tr_y], capacity=64 * 8)
    x, y = tf.train.shuffle_batch(data_queue, num_threads=8, batch_size=cfg.batch_size, capacity=cfg.batch_size * 64,
                                  min_after_dequeue=cfg.batch_size * 32, allow_smaller_final_batch=False)

    return (x, y)


def load_cifar100(is_training):
    # https://keras.io/datasets/
    # https://www.cs.toronto.edu/~kriz/cifar.html:
    # "Each image comes with a 'fine' label (the class to which it belongs)
    # and a 'coarse' label (the superclass to which it belongs)."
    assert(K.image_data_format() == 'channels_last')
    if is_training:
        return cifar100.load_data(label_mode='fine')[0]
    else:
        return cifar100.load_data(label_mode='fine')[1]
