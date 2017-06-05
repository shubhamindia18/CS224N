import os
import getpass
import sys
import time

import numpy as np
import tensorflow as tf
from q2_initialization import xavier_weight_init
import data_utils.utils as du
import data_utils.ner as ner
from utils import data_iterator
from model import LanguageModel

class Config(object):
  """Holds model hyperparams and data information.

  The config class is used to store various hyperparameters and dataset
  information parameters. Model objects are passed a Config() object at
  instantiation.
  """
  embed_size = 50
  batch_size = 64
  label_size = 5
  hidden_size = 100
  max_epochs = 50
  early_stopping = 25
  dropout = 0.9
  lr = 0.000479
  l2 = 0.007018
  window_size = 3

class NERModel(LanguageModel):
  """Implements a NER (Named Entity Recognition) model.

  This class implements a deep network for named entity recognition. It
  inherits from LanguageModel, which has an add_embedding method in addition to
  the standard Model method.
  """

  def load_data(self, debug=False):
    """Loads starter word-vectors and train/dev/test data."""
    # Load the starter word vectors
    self.wv, word_to_num, num_to_word = ner.load_wv(
      'data/ner/vocab.txt', 'data/ner/wordVectors.txt')
    tagnames = ['O', 'LOC', 'MISC', 'ORG', 'PER']
    self.num_to_tag = dict(enumerate(tagnames))
    tag_to_num = {v:k for k,v in self.num_to_tag.iteritems()}

    # Load the training set
    docs = du.load_dataset('data/ner/train')
    self.X_train, self.y_train = du.docs_to_windows(
        docs, word_to_num, tag_to_num, wsize=self.config.window_size)
    if debug:
      self.X_train = self.X_train[:1024]
      self.y_train = self.y_train[:1024]

    # Load the dev set (for tuning hyperparameters)
    docs = du.load_dataset('data/ner/dev')
    self.X_dev, self.y_dev = du.docs_to_windows(
        docs, word_to_num, tag_to_num, wsize=self.config.window_size)
    if debug:
      self.X_dev = self.X_dev[:1024]
      self.y_dev = self.y_dev[:1024]

    # Load the test set (dummy labels only)
    docs = du.load_dataset('data/ner/test.masked')
    self.X_test, self.y_test = du.docs_to_windows(
        docs, word_to_num, tag_to_num, wsize=self.config.window_size)

  def add_placeholders(self):
    """Generate placeholder variables to represent the input tensors

    These placeholders are used as inputs by the rest of the model building
    code and will be fed data during training.  Note that when "None" is in a
    placeholder's shape, it's flexible

    Adds following nodes to the computational graph

    input_placeholder: Input placeholder tensor of shape
                       (None, window_size), type tf.int32
    labels_placeholder: Labels placeholder tensor of shape
                        (None, label_size), type tf.float32
    dropout_placeholder: Dropout value placeholder (scalar),
                         type tf.float32

    Add these placeholders to self as the instance variables
  
      self.input_placeholder
      self.labels_placeholder
      self.dropout_placeholder

    (Don't change the variable names)
    """
    ### YOUR CODE HERE

    self.input_placeholder = tf.placeholder(dtype=tf.int32, shape = (None,self.config.window_size))
    self.labels_placeholder = tf.placeholder(dtype=tf.float32, shape = (None, self.config.label_size))
    self.dropout_placeholder = tf.placeholder(dtype=tf.float32)


    ### END YOUR CODE

  def create_feed_dict(self, input_batch, dropout, label_batch=None):
    """Creates the feed_dict for softmax classifier.

    A feed_dict takes the form of:

    feed_dict = {
        <placeholder>: <tensor of values to be passed for placeholder>,
        ....
    }


    Hint: The keys for the feed_dict should be a subset of the placeholder
          tensors created in add_placeholders.
    Hint: When label_batch is None, don't add a labels entry to the feed_dict.
    
    Args:
      input_batch: A batch of input data.
      label_batch: A batch of label data.
    Returns:
      feed_dict: The feed dictionary mapping from placeholders to values.
    """
    ### YOUR CODE HERE
    feed_dict = {}
    feed_dict[self.input_placeholder] = input_batch
    feed_dict[self.dropout_placeholder] = dropout

    if np.any(label_batch):
      feed_dict[self.labels_placeholder] = label_batch

    ### END YOUR CODE
    return feed_dict

  def add_embedding(self):
    """Add embedding layer that maps from vocabulary to vectors.

    Creates an embedding tensor (of shape (len(self.wv), embed_size). Use the
    input_placeholder to retrieve the embeddings for words in the current batch.

    (Words are discrete entities. They need to be transformed into vectors for use
    in deep-learning. Although we won't do so in this problem, in practice it's
    useful to initialize the embedding with pre-trained word-vectors. For this
    problem, using the default initializer is sufficient.)

    Hint: This layer should use the input_placeholder to index into the
          embedding.
    Hint: You might find tf.nn.embedding_lookup useful.
    Hint: See following link to understand what -1 in a shape means.
      https://www.tensorflow.org/versions/r0.8/api_docs/python/array_ops.html#reshape
    Hint: Check the last slide from the TensorFlow lecture.
    Hint: Here are the dimensions of the variables you will need to create:

      L: (len(self.wv), embed_size)

    Returns:
      window: tf.Tensor of shape (-1, window_size*embed_size)
    """
    # The embedding lookup is currently only implemented for the CPU
    with tf.device('/cpu:0'): # this will pin the variable to cpu
      ### YOUR CODE HERE
      L = tf.Variable(tf.random_normal([len(self.wv),self.config.embed_size]), name = "embedding")
      window = tf.nn.embedding_lookup(L, self.input_placeholder) # this will be of the shape (len(input_placeholder), window_size,embed_size)
      window = tf.reshape(window, shape = (-1, self.config.window_size*self.config.embed_size))
      ### END YOUR CODE
      return window

  def add_model(self, window):
    """Adds the 1-hidden-layer NN.

    Hint: Use a variable_scope (e.g. "Layer") for the first hidden layer, and
          another variable_scope (e.g. "Softmax") for the linear transformation
          preceding the softmax. Make sure to use the xavier_weight_init you
          defined in the previous part to initialize weights.
    Hint: Make sure to add in regularization and dropout to this network.
          Regularization should be an addition to the cost function, while
          dropout should be added after both variable scopes.
    Hint: You might consider using a tensorflow Graph Collection (e.g
          "total_loss") to collect the regularization and loss terms (which you
          will add in add_loss_op below).
    Hint: Here are the dimensions of the various variables you will need to
          create

          W:  (window_size*embed_size, hidden_size)
          b1: (hidden_size,)
          U:  (hidden_size, label_size)
          b2: (label_size)

    https://www.tensorflow.org/versions/r0.7/api_docs/python/framework.html#graph-collections
    Args:
      window: tf.Tensor of shape (-1, window_size*embed_size)
    Returns:
      output: tf.Tensor of shape (batch_size, label_size)
    """
    ### YOUR CODE HERE
    window_size = self.config.window_size
    embed_size = self.config.embed_size
    hidden_size = self.config.hidden_size
    label_size = self.config.label_size

    with tf.variable_scope('layer'):
      W = tf.get_variable('weights', shape = (window_size*embed_size,hidden_size), initializer=xavier_weight_init(), regularizer =tf.contrib.layers.l2_regularizer(scale = self.config.l2) )
      b1 = tf.get_variable('bias', shape = (1, hidden_size), initializer= tf.constant_initializer(0.0))
      layer1 = tf.tanh(tf.matmul(window,W) + b1)
      layer1_dropout = tf.nn.dropout(layer1, self.dropout_placeholder)
    with tf.variable_scope('softmax'):
      U = tf.get_variable('weights', shape =(hidden_size,label_size), initializer= xavier_weight_init(), regularizer =tf.contrib.layers.l2_regularizer(scale = self.config.l2))
      b2 = tf.get_variable('bias', shape = (1, label_size), initializer=tf.constant_initializer(0.0))
      layer2 = tf.matmul(layer1_dropout, U) +  b2 # we are not applying softmax here, instead will call tf.nn.softmax_cross_entropy_with_logits below
      output = tf.nn.dropout(layer2, self.dropout_placeholder)
    ### END YOUR CODE
    return output 

  def add_loss_op(self, y):
    """Adds cross_entropy_loss ops to the computational graph.

    Hint: You can use tf.nn.softmax_cross_entropy_with_logits to simplify your
          implementation. You might find tf.reduce_mean useful.
    Args:
      pred: A tensor of shape (batch_size, n_classes)
    Returns:
      loss: A 0-d tensor (scalar)
    """
    ### YOUR CODE HERE
    loss = tf.nn.softmax_cross_entropy_with_logits(labels = self.labels_placeholder, logits = y)
    loss = tf.reduce_mean(loss)
    loss += sum(tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES))

    tf.summary.scalar('loss', loss)

    ### END YOUR CODE
    return loss

  def add_training_op(self, loss):
    """Sets up the training Ops.

    Creates an optimizer and applies the gradients to all trainable variables.
    The Op returned by this function is what must be passed to the
    `sess.run()` call to cause the model to train. See 

    https://www.tensorflow.org/versions/r0.7/api_docs/python/train.html#Optimizer

    for more information.

    Hint: Use tf.train.AdamOptimizer for this model.
          Calling optimizer.minimize() will return a train_op object.

    Args:
      loss: Loss tensor, from cross_entropy_loss.
    Returns:
      train_op: The Op for training.
    """
    ### YOUR CODE HERE
    opt = tf.train.AdamOptimizer()
    train_op = opt.minimize(loss)
    ### END YOUR CODE
    return train_op

  def __init__(self, config):
    """Constructs the network using the helper functions defined above."""
    self.config = config
    self.load_data(debug=False)
    self.add_placeholders()
    window = self.add_embedding()
    y = self.add_model(window)

    self.loss = self.add_loss_op(y)
    self.predictions = tf.nn.softmax(y)
    one_hot_prediction = tf.argmax(self.predictions, 1)
    correct_prediction = tf.equal(
        tf.argmax(self.labels_placeholder, 1), one_hot_prediction)
    self.correct_predictions = tf.reduce_sum(tf.cast(correct_prediction, 'int32'))
    self.train_op = self.add_training_op(self.loss)

  def run_epoch(self, session, input_data, input_labels,
                shuffle=True, verbose=True):
    orig_X, orig_y = input_data, input_labels
    dp = self.config.dropout
    # We're interested in keeping track of the loss and accuracy during training
    total_loss = []
    total_correct_examples = 0
    total_processed_examples = 0
    total_steps = len(orig_X) / self.config.batch_size
    for step, (x, y) in enumerate(
      data_iterator(orig_X, orig_y, batch_size=self.config.batch_size,
                   label_size=self.config.label_size, shuffle=shuffle)):
      feed = self.create_feed_dict(input_batch=x, dropout=dp, label_batch=y)
      loss, total_correct, _ , merged= session.run(
          [self.loss, self.correct_predictions, self.train_op,  self.merged ],
          feed_dict=feed)
      total_processed_examples += len(x)
      total_correct_examples += total_correct
      total_loss.append(loss)

      if verbose and step % verbose == 0:
        sys.stdout.write('\r{} / {} : loss = {}'.format(
            step, total_steps, np.mean(total_loss)))
        sys.stdout.flush()
    if verbose:
        sys.stdout.write('\r')
        sys.stdout.flush()
    return np.mean(total_loss), total_correct_examples / float(total_processed_examples), merged

  def predict(self, session, X, y=None):
    """Make predictions from the provided model."""
    # If y is given, the loss is also calculated
    # We deactivate dropout by setting it to 1
    dp = 1
    losses = []
    results = []
    if np.any(y):
        data = data_iterator(X, y, batch_size=self.config.batch_size,
                             label_size=self.config.label_size, shuffle=False)
    else:
        data = data_iterator(X, batch_size=self.config.batch_size,
                             label_size=self.config.label_size, shuffle=False)
    for step, (x, y) in enumerate(data):
      feed = self.create_feed_dict(input_batch=x, dropout=dp)
      if np.any(y):
        feed[self.labels_placeholder] = y
        loss, preds = session.run(
            [self.loss, self.predictions], feed_dict=feed)
        losses.append(loss)
      else:
        preds = session.run(self.predictions, feed_dict=feed)
      predicted_indices = preds.argmax(axis=1)
      results.extend(predicted_indices)
    return np.mean(losses), results

def print_confusion(confusion, num_to_tag):
    """Helper method that prints confusion matrix."""
    # Summing top to bottom gets the total number of tags guessed as T
    total_guessed_tags = confusion.sum(axis=0)
    # Summing left to right gets the total number of true tags
    total_true_tags = confusion.sum(axis=1)
    print
    print confusion
    for i, tag in sorted(num_to_tag.items()):
        prec = confusion[i, i] / float(total_guessed_tags[i])
        recall = confusion[i, i] / float(total_true_tags[i])
        print 'Tag: {} - P {:2.4f} / R {:2.4f}'.format(tag, prec, recall)

def calculate_confusion(config, predicted_indices, y_indices):
    """Helper method that calculates confusion matrix."""
    confusion = np.zeros((config.label_size, config.label_size), dtype=np.int32)
    for i in xrange(len(y_indices)):
        correct_label = y_indices[i]
        guessed_label = predicted_indices[i]
        confusion[correct_label, guessed_label] += 1
    return confusion

def save_predictions(predictions, filename):
  """Saves predictions to provided file."""
  with open(filename, "wb") as f:
    for prediction in predictions:
      f.write(str(prediction) + "\n")

def hyperparameter_search_NER():
  """Test NER model implementation.

  You can use this function to test your implementation of the Named Entity
  Recognition network. When debugging, set max_epochs in the Config object to 1
  so you can rapidly iterate.
  """

  learn_list = 10**np.random.uniform(-4,-2, 5)
  reg_list = 10**np.random.uniform(-4, -2, 5)
  from collections import OrderedDict

  # initialising the valid dict
  valid_dict = OrderedDict()
  for learn in learn_list:
    for reg in reg_list:
      valid_dict['l_{}_r{}'.format(learn, reg)]=[]

  for learn in learn_list:
    for reg in reg_list:
      config = Config()
      config.l2 = reg
      config.lr = learn
      with tf.Graph().as_default():
        model = NERModel(config)

        init = tf.initialize_all_variables()
        saver = tf.train.Saver()

        with tf.Session() as session:
          best_val_loss = float('inf')
          best_val_epoch = 0

          session.run(init)
          model.merged = tf.summary.merge_all()
          train_writer = tf.summary.FileWriter( './train',tf.get_default_graph())
          test_writer = tf.summary.FileWriter( './test')

          for epoch in xrange(config.max_epochs):
            print 'Epoch {}'.format(epoch)
            start = time.time()
            ###
            train_loss, train_acc, summary = model.run_epoch(session, model.X_train,
                                                    model.y_train)

            train_writer.add_summary(summary, epoch)
            val_loss, predictions = model.predict(session, model.X_dev, model.y_dev)

            print 'Training loss: {}'.format(train_loss)
            print 'Training acc: {}'.format(train_acc)
            print 'Validation loss: {}'.format(val_loss)

            valid_dict['l_{}_r{}'.format(learn, reg)].append(val_loss)
            if val_loss < best_val_loss:
              best_val_loss = val_loss
              best_val_epoch = epoch
              if not os.path.exists("./weights"):
                os.makedirs("./weights")

              saver.save(session, './weights/ner.weights_l{}_r{}'.format(learn, reg))

            if epoch - best_val_epoch > config.early_stopping:
              break
            ###
            confusion = calculate_confusion(config, predictions, model.y_dev)
            print_confusion(confusion, model.num_to_tag)
            print 'Total time: {}'.format(time.time() - start)


          train_writer.close()
          saver.restore(session, './weights/ner.weights_l{}_r{}'.format(learn, reg))
          print 'Test'
          print '=-=-='
          print "Best valid loss :", best_val_loss
          print "Best valid epoch:", best_val_epoch
          print "Learn:", learn
          print "Reg:", reg
          print 'Writing predictions to q2_test.predicted'
          _, predictions = model.predict(session, model.X_test, model.y_test)
          save_predictions(predictions, "q2_test.predicted_l{}_r{}".format(learn, reg))

  import pickle
  pickle.dump(valid_dict, open("./valid_dict", 'wb'))

  # plotting the validation loss graphs
  import matplotlib.pyplot as plt


  plt.figure(figsize=(20, 10))
  for learn in learn_list:
    for reg in reg_list:
      plt.plot(valid_dict['l_{}_r{}'.format(learn, reg)], label='l_{}_r{}'.format(learn, reg))
      plt.legend()
      plt.tight_layout()

  plt.savefig('learning curve.png')

def test_NER():
  """Test NER model implementation.

  You can use this function to test your implementation of the Named Entity
  Recognition network. When debugging, set max_epochs in the Config object to 1
  so you can rapidly iterate.
  """
  valid_list = []
  train_list = []

  config = Config()
  with tf.Graph().as_default():
    model = NERModel(config)

    init = tf.initialize_all_variables()
    saver = tf.train.Saver()

    with tf.Session() as session:
      best_val_loss = float('inf')
      best_val_epoch = 0

      session.run(init)
      model.merged = tf.summary.merge_all()
      train_writer = tf.summary.FileWriter( './train',tf.get_default_graph())
      test_writer = tf.summary.FileWriter( './test')

      for epoch in xrange(config.max_epochs):
        print 'Epoch {}'.format(epoch)
        start = time.time()
        ###
        train_loss, train_acc, summary = model.run_epoch(session, model.X_train,
                                                model.y_train)

        train_writer.add_summary(summary, epoch)
        val_loss, predictions = model.predict(session, model.X_dev, model.y_dev)

        print 'Training loss: {}'.format(train_loss)
        print 'Training acc: {}'.format(train_acc)
        print 'Validation loss: {}'.format(val_loss)

        valid_list.append(val_loss)
        train_list.append(train_loss)
        if val_loss < best_val_loss:
          best_val_loss = val_loss
          best_val_epoch = epoch
          if not os.path.exists("./weights"):
            os.makedirs("./weights")

          saver.save(session, './weights/ner.weights_02')

        if epoch - best_val_epoch > config.early_stopping:
          break
        ###
        confusion = calculate_confusion(config, predictions, model.y_dev)
        print_confusion(confusion, model.num_to_tag)
        print 'Total time: {}'.format(time.time() - start)


      train_writer.close()
      saver.restore(session, './weights/ner.weights_02')
      print 'Test'
      print '=-=-='
      print "Best valid loss :", best_val_loss
      print "Best valid epoch:", best_val_epoch
      print "Learn:", config.lr
      print "Reg:", config.l2
      print 'Writing predictions to q2_test.predicted'
      _, predictions = model.predict(session, model.X_test, model.y_test)
      save_predictions(predictions, "q2_test.predicted_02")

  # plotting the validation loss graphs
  import matplotlib.pyplot as plt


  plt.figure(figsize=(20, 10))
  plt.plot(valid_list, label='valid loss')
  plt.plot(train_list, label='train loss')
  plt.legend()
  plt.tight_layout()

  plt.savefig('learning curve_02.png')


if __name__ == "__main__":
  # hyperparameter_search_NER()
  test_NER()
