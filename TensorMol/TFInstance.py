"""
For the sake of modularity, all direct access to dig
needs to be phased out...
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from TensorMol.TensorData import *
import numpy as np
import cPickle as pickle
import math
import time, os, sys, numbers
import os.path
if (HAS_TF):
	import tensorflow as tf

class Instance:
	"""
	Manages a persistent training network instance
	"""
	def __init__(self, TData_, ele_ = 1 , Name_=None, NetType_=None):
		"""
		Args:
			TData_: a TensorData
			ele_: an element type for this instance.
			Name_ : a name for this instance, attempts to load from checkpoint.
		"""
		# The tensorflow objects go up here.
		self.inshape = None
		self.outshape = None
		self.sess = None
		self.loss = None
		self.output = None
		self.train_op = None
		self.total_loss = None
		self.embeds_placeholder = None
		self.labels_placeholder = None
		self.saver = None
		self.gradient =None
		self.summary_op =None
		self.summary_writer=None
		# The parameters below belong to tensorflow and its graph
		# all tensorflow variables cannot be pickled they are populated by Prepare
		self.PreparedFor=0

		try:
			self.tf_prec
		except:
			self.tf_prec = eval(PARAMS["tf_prec"])
		self.HiddenLayers = PARAMS["HiddenLayers"]
		self.hidden1 = PARAMS["hidden1"]
		self.hidden2 = PARAMS["hidden2"]
		self.hidden3 = PARAMS["hidden3"]
		self.learning_rate = PARAMS["learning_rate"]
		self.momentum = PARAMS["momentum"]
		self.max_steps = PARAMS["max_steps"]
		self.batch_size = PARAMS["batch_size"]
		self.activation_function_type = PARAMS["NeuronType"]
		self.activation_function = None
		self.AssignActivation()

		self.path='./networks/'
		if (Name_ !=  None):
			self.name = Name_
			#self.QueryAvailable() # Should be a sanity check on the data files.
			self.Load() # Network still cannot be used until it is prepared.
			LOGGER.info("raised network: "+self.train_dir)
			return

		self.element = ele_
		self.TData = TData_
		self.tformer = Transformer(PARAMS["InNormRoutine"], PARAMS["OutNormRoutine"], self.element, self.TData.dig.name, self.TData.dig.OType)
		if (not os.path.isdir(self.path)):
			os.mkdir(self.path)
		self.chk_file = ''

		LOGGER.info("self.learning_rate: "+str(self.learning_rate))
		LOGGER.info("self.batch_size: "+str(self.batch_size))
		LOGGER.info("self.max_steps: "+str(self.max_steps))

		self.NetType = "None"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name
		if (self.element != 0):
			self.TData.LoadElementToScratch(self.element, self.tformer)
			self.tformer.Print()
			self.TData.PrintStatus()
			self.inshape = self.TData.dig.eshape
			self.outshape = self.TData.dig.lshape
		return

	def __del__(self):
		if (self.sess != None):
			self.sess.close()
		self.Clean()

	def AssignActivation(self):
		LOGGER.debug("Assigning Activation... %s", PARAMS["NeuronType"])
		try:
			if self.activation_function_type == "relu":
				self.activation_function = tf.nn.relu
			elif self.activation_function_type == "elu":
				self.activation_function = tf.nn.elu
			elif self.activation_function_type == "selu":
				self.activation_function = self.selu
			elif self.activation_function_type == "softplus":
				self.activation_function = tf.nn.softplus
			elif self.activation_function_type == "tanh":
				self.activation_function = tf.tanh
			elif self.activation_function_type == "sigmoid":
				self.activation_function = tf.sigmoid
			else:
				print ("unknown activation function, set to relu")
				self.activation_function = tf.nn.relu
		except Exception as Ex:
			print(Ex)
			print ("activation function not assigned, set to relu")
			self.activation_function = tf.nn.relu
		return

	def evaluate(self, eval_input):
		# Check sanity of input
		if (not np.all(np.isfinite(eval_input))):
			LOGGER.error("WTF, you trying to feed me, garbage?")
			raise Exception("bad digest.")
		if (self.PreparedFor < eval_input.shape[0]):
			self.Prepare(eval_input, eval_input.shape[0])
		return

	def Prepare(self, eval_input, Ncase=1250):
		"""
		Called if only evaluations are being done, by evaluate()
		"""
		self.Clean()
		self.AssignActivation()
		# Always prepare for at least 125,000 cases which is a 50x50x50 grid.
		eval_labels = np.zeros(Ncase)  # dummy labels
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.placeholder_inputs(Ncase)
			self.output = self.inference(self.embeds_placeholder)
			self.saver = tf.train.Saver()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			metafiles = [x for x in os.listdir(self.train_dir) if (x.count('meta')>0)]
			if (len(metafiles)>0):
				most_recent_meta_file=metafiles[0]
				LOGGER.debug("Restoring training from Meta file: "+most_recent_meta_file)
				config = tf.ConfigProto(allow_soft_placement=True)
				self.sess = tf.Session(config=config)
				self.saver = tf.train.import_meta_graph(self.train_dir+'/'+most_recent_meta_file)
				self.saver.restore(self.sess, tf.train.latest_checkpoint(self.train_dir))
		self.PreparedFor = Ncase
		return

	def TrainPrepare(self,  continue_training =False):
		""" Builds the graphs by calling inference """
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.placeholder_inputs(self.batch_size)
			self.output = self.inference(self.embeds_placeholder)
			self.total_loss, self.loss = self.loss_op(self.output, self.labels_placeholder)
			self.train_op = self.training(self.total_loss, self.learning_rate, self.momentum)
			self.summary_op = tf.summary.merge_all()
			init = tf.global_variables_initializer()
			self.saver = tf.train.Saver()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			self.sess.run(init)
			try:
				metafiles = [x for x in os.listdir(self.train_dir) if (x.count('meta')>0)]
				if (len(metafiles)>0):
					most_recent_meta_file=metafiles[0]
					LOGGER.info("Restoring training from Metafile: "+most_recent_meta_file)
					#Set config to allow soft device placement for temporary fix to known issue with Tensorflow up to version 0.12 atleast - JEH
					config = tf.ConfigProto(allow_soft_placement=True)
					self.sess = tf.Session(config=config)
					self.saver = tf.train.import_meta_graph(self.train_dir+'/'+most_recent_meta_file)
					self.saver.restore(self.sess, tf.train.latest_checkpoint(self.train_dir))
			except Exception as Ex:
				LOGGER.error("Restore Failed")
				pass
			self.summary_writer =  tf.summary.FileWriter(self.train_dir, self.sess.graph)
			return

	def Clean(self):
		if (self.sess != None):
			self.sess.close()
		self.sess = None
		self.loss = None
		self.output = None
		self.total_loss = None
		self.train_op = None
		self.embeds_placeholder = None
		self.labels_placeholder = None
		self.saver = None
		self.gradient =None
		self.summary_writer = None
		self.PreparedFor = 0
		self.summary_op = None
		self.activation_function = None
		return

	def SaveAndClose(self):
		print("Saving TFInstance...")
		if (self.TData!=None):
			self.TData.CleanScratch()
		self.Clean()
		#print("Going to pickle...\n",[(attr,type(ins)) for attr,ins in self.__dict__.items()])
		f=open(self.path+self.name+".tfn","wb")
		pickle.dump(self.__dict__, f, protocol=pickle.HIGHEST_PROTOCOL)
		f.close()
		return

	def variable_summaries(self, var):
		"""Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
		with tf.name_scope('summaries'):
			mean = tf.reduce_mean(var)
			tf.summary.scalar('mean', mean)
		with tf.name_scope('stddev'):
			stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
			tf.summary.scalar('stddev', stddev)
			tf.summary.scalar('max', tf.reduce_max(var))
			tf.summary.scalar('min', tf.reduce_min(var))
			tf.summary.histogram('histogram', var)

	# one of these two routines need to be removed I think. -JAP
	def save_chk(self,  step, feed_dict=None):  # this can be included in the Instance
		#cmd="rm  "+self.train_dir+"/"+self.name+"-chk-*"
		#os.system(cmd)
		checkpoint_file_mini = os.path.join(self.train_dir,self.name+'-chk-'+str(step))
		LOGGER.info("Saving Checkpoint file, "+checkpoint_file_mini)
		self.saver.save(self.sess, checkpoint_file_mini)
		return

	#this isn't really the correct way to load()
	# only the local class members (not any TF objects should be unpickled.)
	def Load(self):
		LOGGER.info("Unpickling TFInstance...")
		f = open(self.path+self.name+".tfn","rb")
		import TensorMol.PickleTM
		tmp = TensorMol.PickleTM.UnPickleTM(f)
		self.Clean()
		# All this shit should be deleteable after re-training.
		self.__dict__.update(tmp)
		f.close()
		chkfiles = [x for x in os.listdir(self.train_dir) if (x.count('chk')>0 and x.count('meta')==0)]
		if (len(chkfiles)>0):
			self.chk_file = chkfiles[0]
		else:
			LOGGER.error("Network not found... Traindir:"+self.train_dir)
			LOGGER.error("Traindir contents: "+str(os.listdir(self.train_dir)))
		return

	def _variable_with_weight_decay(self, var_name, var_shape, var_stddev, var_wd):
		"""Helper to create an initialized Variable with weight decay.

		Note that the Variable is initialized with a truncated normal distribution.
		A weight decay is added only if one is specified.

		Args:
		name: name of the variable
		shape: list of ints
		stddev: standard deviation of a truncated Gaussian
		wd: add L2Loss weight decay multiplied by this float. If None, weight
		decay is not added for this Variable.

		Returns:
		Variable Tensor
		"""
		var = tf.Variable(tf.truncated_normal(var_shape, stddev=var_stddev, dtype=self.tf_prec), name=var_name)
		if var_wd is not None:
			try:
				weight_decay = tf.multiply(tf.nn.l2_loss(var), var_wd, name='weight_loss')
			except:
				print("tf.mul() is deprecated in tensorflow 1.0 in favor of tf.multiply(). Please upgrade soon.")
				weight_decay = tf.mul(tf.nn.l2_loss(var), var_wd, name='weight_loss')
			tf.add_to_collection('losses', weight_decay)
		return var

	def dropout_selu(self, x, rate, alpha= -1.7580993408473766, fixedPointMean=0.0, fixedPointVar=1.0, noise_shape=None, seed=None, name=None, training=False):
		"""Dropout to a value with rescaling."""
		def dropout_selu_impl(x, rate, alpha, noise_shape, seed, name):
			keep_prob = 1.0 - rate
			x = tf.convert_to_tensor(x, name="x")
			if isinstance(keep_prob, numbers.Real) and not 0 < keep_prob <= 1:
				raise ValueError("keep_prob must be a scalar tensor or a float in the "
								"range (0, 1], got %g" % keep_prob)
			keep_prob = tf.convert_to_tensor(keep_prob, dtype=x.dtype, name="keep_prob")
			keep_prob.get_shape().assert_is_compatible_with([])

			alpha = tf.convert_to_tensor(alpha, dtype=x.dtype, name="alpha")
			keep_prob.get_shape().assert_is_compatible_with([])

			if tf.contrib.util.constant_value(keep_prob) == 1:
				return x

			noise_shape = noise_shape if noise_shape is not None else tf.shape(x)
			random_tensor = keep_prob
			random_tensor += tf.random_uniform(noise_shape, seed=seed, dtype=x.dtype)
			binary_tensor = tf.floor(random_tensor)
			ret = x * binary_tensor + alpha * (1-binary_tensor)

			a = tf.sqrt(fixedPointVar / (keep_prob *((1-keep_prob) * tf.pow(alpha-fixedPointMean,2) + fixedPointVar)))

			b = fixedPointMean - a * (keep_prob * fixedPointMean + (1 - keep_prob) * alpha)
			ret = a * ret + b
			ret.set_shape(x.get_shape())
			return ret

		with tf.name_scope(name, "dropout", [x]) as name:
			# return dropout_selu_impl(x, rate, alpha, noise_shape, seed, name) if training else array_ops.identity(x)
			return tf.cond(training,
				lambda: dropout_selu_impl(x, rate, alpha, noise_shape, seed, name),
				lambda: tf.identity(x))

	def selu(self, x):
		with tf.name_scope('elu') as scope:
			alpha = 1.6732632423543772848170429916717
			scale = 1.0507009873554804934193349852946
			return scale*tf.where(x>=0.0, x, alpha*tf.nn.elu(x))

	def placeholder_inputs(self, batch_size):
		raise("Populate placeholder_inputs")
		return

	def fill_feed_dict(self, batch_data, embeds_pl, labels_pl):
		"""Fills the feed_dict for training the given step.
		A feed_dict takes the form of:
		feed_dict = {
		<placeholder>: <tensor of values to be passed for placeholder>,
		....
		}
		Args:
		data_set: The set of images and labels, from input_data.read_data_sets()
		embeds_pl: The images placeholder, from placeholder_inputs().
		labels_pl: The labels placeholder, from placeholder_inputs().
		Returns:
		feed_dict: The feed dictionary mapping from placeholders to values.
		"""
		# Don't eat shit.
		if (not np.all(np.isfinite(batch_data[0]))):
			LOGGER.error("I was fed shit")
			raise Exception("DontEatShit")
		if (not np.all(np.isfinite(batch_data[1]))):
			LOGGER.error("I was fed shit")
			raise Exception("DontEatShit")
		feed_dict = {embeds_pl: batch_data[0], labels_pl: batch_data[1],}
		return feed_dict

	def inference(self, inputs):
		"""Builds the network architecture. Number of hidden layers and nodes in each layer defined in TMParams "HiddenLayers".
		Args:
			inputs: input placeholder for training data from Digester.
		Returns:
			output: scalar or vector of OType from Digester.
		"""

		hiddens = []
		for i in range(len(self.HiddenLayers)):
			if i == 0:
				with tf.name_scope('hidden1'):
					weights = self._variable_with_weight_decay(var_name='weights',
									var_shape=(self.inshape+[self.HiddenLayers[i]]),
									var_stddev= 1.0 / math.sqrt(float(self.inshape[0])), var_wd= 0.00)
					biases = tf.Variable(tf.zeros([self.HiddenLayers[i]], dtype=self.tf_prec), name='biases')
					hiddens.append(self.activation_function(tf.matmul(inputs, weights) + biases))
					# tf.scalar_summary('min/' + weights.name, tf.reduce_min(weights))
					# tf.histogram_summary(weights.name, weights)
			else:
				with tf.name_scope('hidden'+str(i+1)):
					weights = self._variable_with_weight_decay(var_name='weights',
									var_shape=[self.HiddenLayers[i-1], self.HiddenLayers[i]],
									var_stddev= 1.0 / math.sqrt(float(self.HiddenLayers[i-1])), var_wd= 0.00)
					biases = tf.Variable(tf.zeros([self.HiddenLayers[i]], dtype=self.tf_prec),name='biases')
					hiddens.append(self.activation_function(tf.matmul(hiddens[-1], weights) + biases))
		with tf.name_scope('regression_linear'):
			weights = self._variable_with_weight_decay(var_name='weights',
							var_shape=[self.HiddenLayers[-1]]+self.outshape,
							var_stddev= 1.0 / math.sqrt(float(self.HiddenLayers[-1])), var_wd= 0.00)
			biases = tf.Variable(tf.zeros(self.outshape, dtype=self.tf_prec), name='biases')
			output = tf.matmul(hiddens[-1], weights) + biases
		return output

	def loss_op(self, output, labels):
		"""
		Calculates the loss from the logits and the labels.
		Args:
		logits: Logits tensor, float - [batch_size, NUM_CLASSES].
		labels: Labels tensor, int32 - [batch_size].
		Returns:
		loss: Loss tensor of type float.
		"""
		raise Exception("Base Loss.")
		return

	def training(self, loss, learning_rate, momentum):
		"""Sets up the training Ops.
		Creates a summarizer to track the loss over time in TensorBoard.
		Creates an optimizer and applies the gradients to all trainable variables.
		The Op returned by this function is what must be passed to the
		`sess.run()` call to cause the model to train.
		Args:
		loss: Loss tensor, from loss().
		learning_rate: The learning rate to use for gradient descent.
		Returns:
		train_op: The Op for training.
		"""
		tf.summary.scalar(loss.op.name, loss)
		optimizer = tf.train.AdamOptimizer(learning_rate)
		#optimizer = tf.train.MomentumOptimizer(learning_rate, momentum)
		global_step = tf.Variable(0, name='global_step', trainable=False)
		train_op = optimizer.minimize(loss, global_step=global_step)
		return train_op

	def train(self, mxsteps, continue_training= False):
		self.TrainPrepare(continue_training)
		test_freq = PARAMS["test_freq"]
		mini_test_loss = 100000000 # some big numbers
		for step in range(1, mxsteps+1):
			self.train_step(step)
			if step%test_freq==0 and step!=0 :
				test_loss, feed_dict = self.test(step)
				if (test_loss < mini_test_loss):
					mini_test_loss = test_loss
					self.save_chk(step,feed_dict)
		self.SaveAndClose()
		return

	def train_step(self,step):
		raise Exception("Cannot Train base...")
		return


	def TrainPrepare(self,  continue_training =False):
		"""Train for a number of steps."""
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.placeholder_inputs(self.batch_size)
			self.output = self.inference(self.embeds_placeholder)
			self.total_loss, self.loss = self.loss_op(self.output, self.labels_placeholder)
			self.train_op = self.training(self.total_loss, self.learning_rate, self.momentum)
			self.summary_op = tf.summary.merge_all()
			init = tf.global_variables_initializer()
			self.saver = tf.train.Saver()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			self.sess.run(init)
			try: # I think this may be broken
				chkfiles = [x for x in os.listdir(self.train_dir) if (x.count('chk')>0 and x.count('meta')==0)]
				metafiles = [x for x in os.listdir(self.train_dir) if (x.count('meta')>0)]
				if (len(metafiles)>0):
					most_recent_meta_file=metafiles[0]
					print("Restoring training from Metafile: ",most_recent_meta_file)
					#Set config to allow soft device placement for temporary fix to known issue with Tensorflow up to version 0.12 atleast - JEH
					config = tf.ConfigProto(allow_soft_placement=True)
					self.sess = tf.Session(config=config)
					self.saver = tf.train.import_meta_graph(self.train_dir+'/'+most_recent_meta_file)
					self.saver.restore(self.sess, tf.train.latest_checkpoint(self.train_dir))
			except Exception as Ex:
				print("Restore Failed 2341325",Ex)
				pass
			self.summary_writer =  tf.summary.FileWriter(self.train_dir, self.sess.graph)
			return

	def test(self,step):
		raise Exception("Base Test")
		return

	def print_training(self, step, loss, Ncase, duration, Train=True):
		denom = max((int(Ncase/self.batch_size)),1)
		if Train:
			LOGGER.info("step: %7d  duration: %.5f train loss: %.10f", step, duration,(float(loss)/(denom*self.batch_size)))
		else:
			LOGGER.info("step: %7d  duration: %.5f test loss: %.10f", step, duration,(float(loss)/(denom*self.batch_size)))
		return

class Instance_fc_classify(Instance):
	def __init__(self, TData_, ele_ = 1 , Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "fc_classify"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name
		self.prob = None
		#		self.inshape = self.TData.scratch_inputs.shape[1]
		self.correct = None
		self.summary_op =None
		self.summary_writer=None

	def n_correct(self, output, labels):
		# For a classifier model, we can use the in_top_k Op.
		# It returns a bool tensor with shape [batch_size] that is true for
		# the examples where the label is in the top k (here k=1)
		# of all logits for that example.
		labels = tf.to_int64(labels)
		correct = tf.nn.in_top_k(output, labels, 1)
		# Return the number of true entries.
		return tf.reduce_sum(tf.cast(correct, tf.int32))

	def evaluate(self, eval_input):
		# Check sanity of input
		Instance.evaluate(self, eval_input)
		eval_input_ = eval_input
		if (self.PreparedFor>eval_input.shape[0]):
			eval_input_ =np.copy(eval_input)
			eval_input_.resize((self.PreparedFor,eval_input.shape[1]))
			# pad with zeros
		eval_labels = np.zeros(self.PreparedFor)  # dummy labels
		batch_data = [eval_input_, eval_labels]
		#embeds_placeholder, labels_placeholder = self.placeholder_inputs(Ncase) Made by Prepare()
		feed_dict = self.fill_feed_dict(batch_data,self.embeds_placeholder,self.labels_placeholder)
		tmp = (np.array(self.sess.run([self.prob], feed_dict=feed_dict))[0,:eval_input.shape[0],1])
		if (not np.all(np.isfinite(tmp))):
			LOGGER.error("TFsession returned garbage")
			LOGGER.error("TFInputs: "+str(eval_input) ) #If it's still a problem here use tf.Print version of the graph.
			raise Exception("Garbage...")
		if (self.PreparedFor > eval_input.shape[0]):
			return tmp[:eval_input.shape[0]]
		return tmp

	def Prepare(self, eval_input, Ncase=1250):
		Instance.Prepare(self)
		LOGGER.info("Preparing a "+self.NetType+"Instance")
		self.prob = None
		self.correct = None
		# Always prepare for at least 125,000 cases which is a 50x50x50 grid.
		eval_labels = np.zeros(Ncase)  # dummy labels
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.placeholder_inputs(Ncase)
			self.output = self.inference(self.embeds_placeholder)
			self.correct = self.n_correct(self.output, self.labels_placeholder)
			self.prob = self.justpreds(self.output)
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			self.saver = tf.train.Saver()
			chkfiles = [x for x in os.listdir(self.train_dir) if (x.count('chk')>0 and x.count('meta')==0)]
			if (len(chkfiles)>0):
				most_recent_chk_file=chkfiles[0]
				LOGGER.info("Restoring training from Checkpoint: "+most_recent_chk_file)
				self.saver.restore(self.sess, self.train_dir+'/'+most_recent_chk_file)
		self.PreparedFor = Ncase
		return

	def Save(self):
		self.prob = None
		self.correct = None
		self.summary_op =None
		self.summary_writer=None
		Instance.Save(self)
		return

	def placeholder_inputs(self, batch_size):
		"""Generate placeholder variables to represent the input tensors.
		These placeholders are used as inputs by the rest of the model building
		code and will be fed from the downloaded data in the .run() loop, below.
		Args:
		batch_size: The batch size will be baked into both placeholders.
		Returns:
		embeds_placeholder: Images placeholder.
		labels_placeholder: Labels placeholder.
		"""
		# Note that the shapes of the placeholders match the shapes of the full
		# image and label tensors, except the first dimension is now batch_size
		# rather than the full size of the train or test data sets.
		inputs_pl = tf.placeholder(self.tf_prec, shape=(batch_size,self.inshape)) # JAP : Careful about the shapes... should be flat for now.
		outputs_pl = tf.placeholder(self.tf_prec, shape=(batch_size))
		return inputs_pl, outputs_pl

	def justpreds(self, output):
		"""Calculates the loss from the logits and the labels.
		Args:
		logits: Logits tensor, float - [batch_size, NUM_CLASSES].
		labels: Labels tensor, int32 - [batch_size].
		Returns:
		loss: Loss tensor of type float.
		"""
		prob = tf.nn.softmax(output)
		return prob

	def loss_op(self, output, labels):
		"""Calculates the loss from the logits and the labels.
		Args:
		logits: Logits tensor, float - [batch_size, NUM_CLASSES].
		labels: Labels tensor, int32 - [batch_size].
		Returns:
		loss: Loss tensor of type float.
		"""
		prob = tf.nn.softmax(output)
		labels = tf.to_int64(labels)
		cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(output, labels, name='xentropy')
		cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
		tf.add_to_collection('losses', cross_entropy_mean)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), cross_entropy_mean, prob

	def print_training(self, step, loss, total_correct, Ncase, duration):
		denom=max(int(Ncase/self.batch_size),1)
		print("step: ", "%7d"%step, "  duration: ", "%.5f"%duration,  "  train loss: ", "%.10f"%(float(loss)/denom),"accu:  %.5f"%(float(total_correct)/(denom*self.batch_size)))
		return

	def train_step(self,step):
		Ncase_train = self.TData.NTrainCasesInScratch()
		start_time = time.time()
		train_loss =  0.0
		total_correct = 0
		for ministep in range (0, int(Ncase_train/self.batch_size)):
			batch_data=self.TData.GetTrainBatch(self.element,  self.batch_size) #advances the case pointer in TData...
			feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			_, total_loss_value, loss_value, prob_value, correct_num  = self.sess.run([self.train_op, self.total_loss, self.loss, self.prob, self.correct], feed_dict=feed_dict)
			train_loss = train_loss + loss_value
			total_correct = total_correct + correct_num
		duration = time.time() - start_time
		#self.print_training(step, train_loss, total_correct, Ncase_train, duration)
		self.print_training(step, train_loss, Ncase_train, duration)
		return

	def test(self, step):
		Ncase_test = self.TData.NTest
		test_loss =  0.0
		test_correct = 0.
		test_start_time = time.time()
		test_loss = None
		feed_dict = None
		for  ministep in range (0, int(Ncase_test/self.batch_size)):
			batch_data=self.TData.GetTestBatch(self.element,  self.batch_size, ministep)
			feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			loss_value, prob_value, test_correct_num = self.sess.run([ self.loss, self.prob, self.correct],  feed_dict=feed_dict)
			test_loss = test_loss + loss_value
			test_correct = test_correct + test_correct_num
			duration = time.time() - test_start_time
			LOGGER.info("testing...")
			self.print_training(step, test_loss, test_correct, Ncase_test, duration)
		return test_loss, feed_dict

class Instance_fc_sqdiff(Instance):
	def __init__(self, TData_, ele_ = 1 , Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "fc_sqdiff"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name

	def evaluate(self, eval_input):
		# Check sanity of input
		Instance.evaluate(self, eval_input)
		given_cases = eval_input.shape[0]
		#print("given_cases:", given_cases)
		eis = list(eval_input.shape)
		eval_input_ = eval_input.copy()
		if (self.PreparedFor > given_cases):
			eval_input_.resize(([self.PreparedFor]+eis[1:]))
			# pad with zeros
		eval_labels = np.zeros(tuple([self.PreparedFor]+list(self.outshape)))  # dummy labels
		batch_data = [eval_input_, eval_labels]
		#embeds_placeholder, labels_placeholder = self.placeholder_inputs(Ncase) Made by Prepare()
		feed_dict = self.fill_feed_dict(batch_data,self.embeds_placeholder, self.labels_placeholder)
		tmp = np.array(self.sess.run([self.output], feed_dict=feed_dict))
		if (not np.all(np.isfinite(tmp))):
			LOGGER.error("TFsession returned garbage")
			LOGGER.error("TFInputs"+str(eval_input) ) #If it's still a problem here use tf.Print version of the graph.
		return tmp[0,:given_cases]

	def Save(self):
		self.summary_op =None
		self.summary_writer=None
		Instance.Save(self)
		return

	def placeholder_inputs(self, batch_size):
		"""Generate placeholder variables to represent the input tensors.
		These placeholders are used as inputs by the rest of the model building
		code and will be fed from the downloaded data in the .run() loop, below.
		Args:
		batch_size: The batch size will be baked into both placeholders.
		Returns:
		embeds_placeholder: Images placeholder.
		labels_placeholder: Labels placeholder.
		"""
		# Note that the shapes of the placeholders match the shapes of the full
		# image and label tensors, except the first dimension is now batch_size
		# rather than the full size of the train or test data sets.
		inputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size]+list(self.inshape)))
		outputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size]+list(self.outshape)))
		return inputs_pl, outputs_pl

	def loss_op(self, output, labels):
		try:
			diff  = tf.subtract(output, labels)
		except:
			print("tf.sub() is deprecated in tensorflow 1.0 in favor of tf.subtract(). Please upgrade soon.")
			diff  = tf.sub(output, labels)
		loss = tf.nn.l2_loss(diff)
		tf.add_to_collection('losses', loss)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), loss

	def train_step(self,step):
		Ncase_train = self.TData.NTrainCasesInScratch()
		start_time = time.time()
		train_loss =  0.0
		total_correct = 0
		for ministep in range (0, int(Ncase_train/self.batch_size)):
			batch_data=self.TData.GetTrainBatch(self.element,  self.batch_size) #advances the case pointer in TData...
			feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			_, total_loss_value, loss_value = self.sess.run([self.train_op, self.total_loss, self.loss], feed_dict=feed_dict)
			train_loss = train_loss + loss_value
		duration = time.time() - start_time
		#self.print_training(step, train_loss, total_correct, Ncase_train, duration)
		self.print_training(step, train_loss, Ncase_train, duration)
		return

	def test(self, step):
		Ncase_test = self.TData.NTestCasesInScratch()
		test_loss =  0.0
		test_start_time = time.time()
		#for ministep in range (0, int(Ncase_test/self.batch_size)):
		batch_data=self.TData.GetTestBatch(self.element,  self.batch_size)#, ministep)
		feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
		preds, total_loss_value, loss_value  = self.sess.run([self.output, self.total_loss,  self.loss],  feed_dict=feed_dict)
		self.TData.EvaluateTestBatch(batch_data[1],preds, self.tformer)
		test_loss = test_loss + loss_value
		duration = time.time() - test_start_time
		print("testing...")
		self.print_training(step, test_loss,  Ncase_test, duration, Train=False)
		return test_loss, feed_dict

	def PrepareData(self, batch_data):
		if (batch_data[0].shape[0]==self.batch_size):
			batch_data=[batch_data[0], batch_data[1].reshape((batch_data[1].shape[0],1))]
		elif (batch_data[0].shape[0] < self.batch_size):
			batch_data=[batch_data[0], batch_data[1].reshape((batch_data[1].shape[0],1))]
			tmp_input = np.copy(batch_data[0])
			tmp_output = np.copy(batch_data[1])
			tmp_input.resize((self.batch_size,  batch_data[0].shape[1]))
			tmp_output.resize((self.batch_size,  batch_data[1].shape[1]))
			batch_data=[ tmp_input, tmp_output]
		return batch_data

class Instance_fc_sqdiff_BP_pair(Instance_fc_sqdiff):
	def __init__(self, TData_, ele_=1, Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "fc_sqdiff_BP_pair"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name

	def inference(self, inp_pl, index_pl):
		"""
		Builds a Behler-Parinello graph

		Args:
			inp_pl: a list of (num_of atom type X flattened input shape) matrix of input cases.
			index_pl: a list of (num_of atom type X batchsize) array which linearly combines the elements
		Returns:
			The BP graph output
		"""
		# convert the index matrix from bool to float
		branches=[]
		atom_outputs = []
		hidden1_units=self.hidden1
		hidden2_units=self.hidden2
		hidden3_units=self.hidden3

		#output = gen_state_ops._temporary_variable(shape=[self.batch_size_output], dtype=self.tf_prec)
		#output = state_ops.assign(output, array_ops.zeros_like(index_pl))
		#output = tf.Variable(output_pl)
		#output = tf.Variable(tf.zeros([self.batch_size_output], dtype=self.tf_prec))
		output = tf.zeros([self.batch_size_output], dtype=self.tf_prec)
		nrm1=1.0/(10+math.sqrt(float(self.inshape)))
		nrm2=1.0/(10+math.sqrt(float(hidden1_units)))
		nrm3=1.0/(10+math.sqrt(float(hidden2_units)))
		nrm4=1.0/(10+math.sqrt(float(hidden3_units)))
		print("Norms:", nrm1,nrm2,nrm3)
		LOGGER.info("Layer initial Norms: %f %f %f", nrm1,nrm2,nrm3)
		#print(inp_pl)
		#tf.Print(inp_pl, [inp_pl], message="This is input: ",first_n=10000000,summarize=100000000)
		#tf.Print(bnds_pl, [bnds_pl], message="bnds_pl: ",first_n=10000000,summarize=100000000)
		#tf.Print(mats_pl, [mats_pl], message="mats_pl: ",first_n=10000000,summarize=100000000)
		for e in range(len(self.eles)):
			branches.append([])
			inputs = inp_pl[e]
			shp_in = tf.shape(inputs)
			index = index_pl[e]
			if (PARAMS["check_level"]>2):
				tf.Print(tf.to_float(shp_in), [tf.to_float(shp_in)], message="Element "+str(e)+"input shape ",first_n=10000000,summarize=100000000)
				index_shape = tf.shape(index)
				tf.Print(tf.to_float(index_shape), [tf.to_float(index_shape)], message="Element "+str(e)+"index shape ",first_n=10000000,summarize=100000000)
			if (PARAMS["check_level"]>3):
				tf.Print(tf.to_float(inputs), [tf.to_float(inputs)], message="This is input shape ",first_n=10000000,summarize=100000000)
			with tf.name_scope(str(self.eles[e])+'_hidden_1'):
				weights = self._variable_with_weight_decay(var_name='weights', var_shape=[self.inshape, hidden1_units], var_stddev=nrm1, var_wd=0.001)
				biases = tf.Variable(tf.zeros([hidden1_units], dtype=self.tf_prec), name='biases')
				branches[-1].append(self.activation_function(tf.matmul(inputs, weights) + biases))
			with tf.name_scope(str(self.eles[e])+'_hidden_2'):
				weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden1_units, hidden2_units], var_stddev=nrm2, var_wd=0.001)
				biases = tf.Variable(tf.zeros([hidden2_units], dtype=self.tf_prec), name='biases')
				branches[-1].append(self.activation_function(tf.matmul(branches[-1][-1], weights) + biases))
			with tf.name_scope(str(self.eles[e])+'_hidden_3'):
				weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden2_units, hidden3_units], var_stddev=nrm3, var_wd=0.001)
				biases = tf.Variable(tf.zeros([hidden3_units], dtype=self.tf_prec), name='biases')
				branches[-1].append(self.activation_function(tf.matmul(branches[-1][-1], weights) + biases))
				#tf.Print(branches[-1], [branches[-1]], message="This is layer 2: ",first_n=10000000,summarize=100000000)
			with tf.name_scope(str(self.eles[e])+'_regression_linear'):
				shp = tf.shape(inputs)
				weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden3_units, 1], var_stddev=nrm4, var_wd=None)
				biases = tf.Variable(tf.zeros([1], dtype=self.tf_prec), name='biases')
				branches[-1].append(tf.matmul(branches[-1][-1], weights) + biases)
				shp_out = tf.shape(branches[-1][-1])
				cut = tf.slice(branches[-1][-1],[0,0],[shp_out[0],1])
				#tf.Print(tf.to_float(shp_out), [tf.to_float(shp_out)], message="This is outshape: ",first_n=10000000,summarize=100000000)
				rshp = tf.reshape(cut,[1,shp_out[0]])
				atom_outputs.append(rshp)
				rshpflat = tf.reshape(cut,[shp_out[0]])
				range_index = tf.range(tf.cast(shp_out[0], tf.int64), dtype=tf.int64)
				sparse_index =tf.stack([index, range_index], axis=1)
				sp_atomoutputs = tf.SparseTensor(sparse_index, rshpflat, dense_shape=[tf.cast(self.batch_size_output, tf.int64), tf.cast(shp_out[0], tf.int64)])
				mol_tmp = tf.sparse_reduce_sum(sp_atomoutputs, axis=1)
				output = tf.add(output, mol_tmp)
		tf.verify_tensor_all_finite(output,"Nan in output!!!")
		#tf.Print(output, [output], message="This is output: ",first_n=10000000,summarize=100000000)
		return output, atom_outputs

class Instance_del_fc_sqdiff(Instance_fc_sqdiff):
	def __init__(self, TData_, ele_=1, Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "del_fc_sqdiff"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name

	def inference(self, inputs, bleep, bloop, blop):
		"""Build the MNIST model up to where it may be used for inference.
		Args:
		images: Images placeholder, from inputs().
		hidden1_units: Size of the first hidden layer.
		hidden2_units: Size of the second hidden layer.
		Returns:
		softmax_linear: Output tensor with the computed logits.
		"""
		hidden1_units = PARAMS["hidden1"]
		hidden2_units = PARAMS["hidden2"]
		hidden3_units = PARAMS["hidden3"]
		LOGGER.debug("hidden1_units: "+str(hidden1_units))
		LOGGER.debug("hidden2_units: "+str(hidden2_units))
		LOGGER.debug("hidden3_units: "+str(hidden3_units))
		# Hidden 1
		with tf.name_scope('hidden1'):
			weights = self._variable_with_weight_decay(var_name='weights', var_shape=list(self.inshape)+[hidden1_units], var_stddev= 0.4 / math.sqrt(float(self.inshape[0])), var_wd= 0.00)
			biases = tf.Variable(tf.zeros([hidden1_units], dtype=self.tf_prec), name='biases')
			hidden1 = tf.nn.relu(tf.matmul(inputs[:-3], weights) + biases)
			#tf.summary.scalar('min/' + weights.name, tf.reduce_min(weights))
			#tf.summary.histogram(weights.name, weights)
		# Hidden 2
		with tf.name_scope('hidden2'):
			weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden1_units, hidden2_units], var_stddev= 0.4 / math.sqrt(float(hidden1_units)), var_wd= 0.00)
			biases = tf.Variable(tf.zeros([hidden2_units], dtype=self.tf_prec),name='biases')
			hidden2 = tf.nn.relu(tf.matmul(hidden1, weights) + biases)

		# Hidden 3
		with tf.name_scope('hidden3'):
			weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden2_units, hidden3_units], var_stddev= 0.4 / math.sqrt(float(hidden2_units)), var_wd= 0.00)
			biases = tf.Variable(tf.zeros([hidden3_units], dtype=self.tf_prec),name='biases')
			hidden3 = tf.nn.relu(tf.matmul(hidden2, weights) + biases)
		#Delta Layer
		with tf.name_scope('delta_layer'):
			weights = self._variable_with_weight_decay(var_name='weights', var_shape=[hidden3_units]+ list(2*self.outshape), var_stddev= 0.4 / math.sqrt(float(hidden3_units)), var_wd= 0.00)
			biases = tf.Variable(tf.zeros(self.outshape, dtype=self.tf_prec), name='biases')
			delta = tf.matmul(hidden3, weights) + biases
		# Linear
		with tf.name_scope('regression_linear'):
			delta_out = tf.multiply(tf.slice(delta,[self.outshape],[self.outshape]),inputs[-3:])
			output = tf.add(tf.slice(delta,[0],[self.outshape]),delta_out)
		return output

	def loss_op(self, output, labels):
		diff  = tf.subtract(output, labels)
		loss = tf.nn.l2_loss(diff)
		tf.add_to_collection('losses', loss)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), loss

class Instance_conv2d_sqdiff(Instance):
	def __init__(self, TData_, ele_ = 1 , Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "conv2d_sqdiff"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name

	def placeholder_inputs(self, batch_size):
		"""Generate placeholder variables to represent the input tensors.
		These placeholders are used as inputs by the rest of the model building
		code and will be fed from the downloaded data in the .run() loop, below.
		Args:
		batch_size: The batch size will be baked into both placeholders.
		Returns:
		embeds_placeholder: Images placeholder.
		labels_placeholder: Labels placeholder.
		"""
		# Note that the shapes of the placeholders match the shapes of the full
		# image and label tensors, except the first dimension is now batch_size
		# rather than the full size of the train or test data sets.
		inputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size,self.inshape]))
		outputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size, self.outshape]))
		return inputs_pl, outputs_pl

	def _weight_variable(self, name, shape):
		return tf.get_variable(name, shape, self.tf_prec, tf.truncated_normal_initializer(stddev=0.01))

	def _bias_variable(self, name, shape):
		return tf.get_variable(name, shape, self.tf_prec, tf.constant_initializer(0.01, dtype=self.tf_prec))

	def conv2d(self, x, W, b, strides=1):
		"""
		2D Convolution wrapper with bias and relu activation
		"""
		x = tf.nn.conv2d(x, W, strides=[1, strides, strides, 1], padding='SAME')
		x = tf.nn.bias_add(x, b)
		return tf.nn.relu(x)

	def inference(self, input):
		FC_SIZE = 512
		with tf.variable_scope('conv1') as scope:
			in_filters = 1
			out_filters = 8
			kernel = self._weight_variable('weights', [2, 2, 2, in_filters, out_filters])
			conv = tf.nn.conv2d(input, kernel, [1, 1, 1, 1], padding='SAME') # third arg. is the strides case,xstride,ystride,zstride,channel stride
			biases = self._bias_variable('biases', [out_filters])
			bias = tf.nn.bias_add(conv, biases)
			conv1 = tf.nn.relu(bias, name=scope.name)
			prev_layer = conv1
			in_filters = out_filters

		# pool1 = tf.nn.max_pool3d(prev_layer, ksize=[1, 3, 3, 3, 1], strides=[1, 2, 2, 2, 1], padding='SAME')
		#norm1 = pool1  # tf.nn.lrn(pool1, 4, bias=1.0, alpha=0.001 / 9.0, beta = 0.75, name='norm1')
		#prev_layer = norm1

		with tf.variable_scope('conv2') as scope:
			out_filters = 16
			kernel = self._weight_variable('weights', [2, 2, 2, in_filters, out_filters])
			conv = tf.nn.conv3d(prev_layer, kernel, [1, 1, 1, 1, 1], padding='SAME')
			biases = self._bias_variable('biases', [out_filters])
			bias = tf.nn.bias_add(conv, biases)
			conv2 = tf.nn.relu(bias, name=scope.name)
			prev_layer = conv2
			in_filters = out_filters

		# normalize prev_layer here
		# prev_layer = tf.nn.max_pool3d(prev_layer, ksize=[1, 3, 3, 3, 1], strides=[1, 2, 2, 2, 1], padding='SAME')

		with tf.variable_scope('local1') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			prev_layer_flat = tf.reshape(prev_layer, [-1, dim])
			weights = self._weight_variable('weights', [dim, FC_SIZE])
			biases = self._bias_variable('biases', [FC_SIZE])
			local1 = tf.nn.relu(tf.matmul(prev_layer_flat, weights) + biases, name=scope.name)
			prev_layer = local1

		with tf.variable_scope('local2') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			prev_layer_flat = tf.reshape(prev_layer, [-1, dim])
			weights = self._weight_variable('weights', [dim, FC_SIZE])
			biases = self._bias_variable('biases', [FC_SIZE])
			local2 = tf.nn.relu(tf.matmul(prev_layer_flat, weights) + biases, name=scope.name)
			prev_layer = local2

		with tf.variable_scope('regression_linear') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			weights = self._weight_variable('weights', [dim]+list(self.outshape))
			biases = self._bias_variable('biases', self.outshape)
			output = tf.add(tf.matmul(prev_layer, weights), biases, name=scope.name)
		return output

	def evaluate(self, eval_input):
		# Check sanity of input
		Instance.evaluate(self, eval_input)
		eval_input_ = eval_input
		if (self.PreparedFor>eval_input.shape[0]):
			eval_input_ =np.copy(eval_input)
			eval_input_.resize(([self.PreparedFor]+self.inshape))
		# pad with zeros
		eval_labels = np.zeros(tuple([self.PreparedFor]+list(self.outshape)))  # dummy labels
		batch_data = self.PrepareData([eval_input_, eval_labels])
		#embeds_placeholder, labels_placeholder = self.placeholder_inputs(Ncase) Made by Prepare()
		feed_dict = self.fill_feed_dict(batch_data,self.embeds_placeholder, self.labels_placeholder)
		tmp = np.array(self.sess.run([self.output], feed_dict=feed_dict))
		if (not np.all(np.isfinite(tmp))):
			LOGGER.error("TFsession returned garbage")
			LOGGER.error("TFInputs"+str(eval_input)) #If it's still a problem here use tf.Print version of the graph.
		if (self.PreparedFor>eval_input.shape[0]):
			return tmp[:eval_input.shape[0]]
		return tmp

	def Save(self):
		self.summary_op =None
		self.summary_writer=None
		Instance.Save(self)
		return

	def loss_op(self, output, labels):
		diff  = tf.slice(tf.sub(output, labels),[0,self.outshape[0]-3],[-1,-1])
		# this only compares direct displacement predictions.
		loss = tf.nn.l2_loss(diff)
		tf.add_to_collection('losses', loss)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), loss

	def train_step(self,step):
		Ncase_train = self.TData.NTrainCasesInScratch()
		start_time = time.time()
		train_loss =  0.0
		total_correct = 0
		for ministep in range (0, int(Ncase_train/self.batch_size)):
			batch_data=self.PrepareData(self.TData.GetTrainBatch(self.element,  self.batch_size)) #advances the case pointer in TData...
			feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			_, total_loss_value, loss_value = self.sess.run([self.train_op, self.total_loss, self.loss], feed_dict=feed_dict)
			train_loss = train_loss + loss_value
		duration = time.time() - start_time
		#self.print_training(step, train_loss, total_correct, Ncase_train, duration)
		self.print_training(step, train_loss, Ncase_train, duration)
		return

	def test(self, step):
		Ncase_test = self.TData.NTestCasesInScratch()
		test_loss =  0.0
		test_start_time = time.time()
		#for ministep in range (0, int(Ncase_test/self.batch_size)):
		batch_data=self.PrepareData(self.TData.GetTestBatch(self.element,  self.batch_size))#, ministep)
		feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
		preds, total_loss_value, loss_value  = self.sess.run([self.output, self.total_loss,  self.loss],  feed_dict=feed_dict)
		self.TData.EvaluateTestBatch(batch_data[1],preds, self.tformer)
		test_loss = test_loss + loss_value
		duration = time.time() - test_start_time
		LOGGER.info("testing...")
		self.print_training(step, test_loss,  Ncase_test, duration)
		return test_loss, feed_dict

	def PrepareData(self, batch_data):

		#for i in range(self.batch_size):
		#	ds=GRIDS.Rasterize(batch_data[0][i])
		#	GridstoRaw(ds, GRIDS.NPts, "Inp"+str(i))

		if (batch_data[0].shape[0]==self.batch_size):
			batch_data=[batch_data[0].reshape(batch_data[0].shape[0],GRIDS.NGau,GRIDS.NGau,GRIDS.NGau,1), batch_data[1]]
		elif (batch_data[0].shape[0] < self.batch_size):
			LOGGER.info("Resizing... ")
			batch_data=[batch_data[0].resize(self.batch_size,GRIDS.NGau,GRIDS.NGau,GRIDS.NGau,1), batch_data[1].resize((self.batch_size,  batch_data[1].shape[1]))]
#			batch_data=[batch_data[0], batch_data[1].reshape((batch_data[1].shape[0],1))]
#			tmp_input = np.copy(batch_data[0])
#			tmp_output = np.copy(batch_data[1])
#			tmp_input.resize((self.batch_size,  batch_data[0].shape[1]))
#			tmp_output.resize((self.batch_size,  batch_data[1].shape[1]))
#			batch_data=[ tmp_input, tmp_output]
		return batch_data

class Instance_3dconv_sqdiff(Instance):
	''' Let's see if a 3d-convolutional network improves the learning rate on the Gaussian grids. '''
	def __init__(self, TData_, ele_ = 1 , Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "3conv_sqdiff"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name

	def placeholder_inputs(self, batch_size):
		"""Generate placeholder variables to represent the input tensors.
		These placeholders are used as inputs by the rest of the model building
		code and will be fed from the downloaded data in the .run() loop, below.
		Args:
		batch_size: The batch size will be baked into both placeholders.
		Returns:
		embeds_placeholder: Images placeholder.
		labels_placeholder: Labels placeholder.
		"""
		# Note that the shapes of the placeholders match the shapes of the full
		# image and label tensors, except the first dimension is now batch_size
		# rather than the full size of the train or test data sets.
		if (self.inshape[0]!=GRIDS.NGau3):
			print("Bad inputs... ", self.inshape)
			raise Exception("Nonsquare")
		inputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size,GRIDS.NGau,GRIDS.NGau,GRIDS.NGau,1]))
		outputs_pl = tf.placeholder(self.tf_prec, shape=tuple([batch_size]+list(self.outshape)))
		return inputs_pl, outputs_pl

	def _weight_variable(self, name, shape):
		return tf.get_variable(name, shape, self.tf_prec, tf.truncated_normal_initializer(stddev=0.01))

	def _bias_variable(self, name, shape):
		return tf.get_variable(name, shape, self.tf_prec, tf.constant_initializer(0.01, dtype=self.tf_prec))

	def inference(self, input):
		FC_SIZE = 512
		with tf.variable_scope('conv1') as scope:
			in_filters = 1
			out_filters = 8
			kernel = self._weight_variable('weights', [2, 2, 2, in_filters, out_filters])
			conv = tf.nn.conv3d(input, kernel, [1, 1, 1, 1, 1], padding='SAME') # third arg. is the strides case,xstride,ystride,zstride,channel stride
			biases = self._bias_variable('biases', [out_filters])
			bias = tf.nn.bias_add(conv, biases)
			conv1 = tf.nn.relu(bias, name=scope.name)
			prev_layer = conv1
			in_filters = out_filters

		# pool1 = tf.nn.max_pool3d(prev_layer, ksize=[1, 3, 3, 3, 1], strides=[1, 2, 2, 2, 1], padding='SAME')
		#norm1 = pool1  # tf.nn.lrn(pool1, 4, bias=1.0, alpha=0.001 / 9.0, beta = 0.75, name='norm1')
		#prev_layer = norm1

		with tf.variable_scope('conv2') as scope:
			out_filters = 16
			kernel = self._weight_variable('weights', [2, 2, 2, in_filters, out_filters])
			conv = tf.nn.conv3d(prev_layer, kernel, [1, 1, 1, 1, 1], padding='SAME')
			biases = self._bias_variable('biases', [out_filters])
			bias = tf.nn.bias_add(conv, biases)
			conv2 = tf.nn.relu(bias, name=scope.name)
			prev_layer = conv2
			in_filters = out_filters

		# normalize prev_layer here
		# prev_layer = tf.nn.max_pool3d(prev_layer, ksize=[1, 3, 3, 3, 1], strides=[1, 2, 2, 2, 1], padding='SAME')

		with tf.variable_scope('local1') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			prev_layer_flat = tf.reshape(prev_layer, [-1, dim])
			weights = self._weight_variable('weights', [dim, FC_SIZE])
			biases = self._bias_variable('biases', [FC_SIZE])
			local1 = tf.nn.relu(tf.matmul(prev_layer_flat, weights) + biases, name=scope.name)
			prev_layer = local1

		with tf.variable_scope('local2') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			prev_layer_flat = tf.reshape(prev_layer, [-1, dim])
			weights = self._weight_variable('weights', [dim, FC_SIZE])
			biases = self._bias_variable('biases', [FC_SIZE])
			local2 = tf.nn.relu(tf.matmul(prev_layer_flat, weights) + biases, name=scope.name)
			prev_layer = local2

		with tf.variable_scope('regression_linear') as scope:
			dim = np.prod(prev_layer.get_shape().as_list()[1:])
			weights = self._weight_variable('weights', [dim]+list(self.outshape))
			biases = self._bias_variable('biases', self.outshape)
			output = tf.add(tf.matmul(prev_layer, weights), biases, name=scope.name)
		return output

	def evaluate(self, eval_input):
		# Check sanity of input
		Instance.evaluate(self, eval_input)
		eval_input_ = eval_input
		if (self.PreparedFor>eval_input.shape[0]):
			eval_input_ =np.copy(eval_input)
			eval_input_.resize(([self.PreparedFor]+self.inshape))
		# pad with zeros
		eval_labels = np.zeros(tuple([self.PreparedFor]+list(self.outshape)))  # dummy labels
		batch_data = self.PrepareData([eval_input_, eval_labels])
		#embeds_placeholder, labels_placeholder = self.placeholder_inputs(Ncase) Made by Prepare()
		feed_dict = self.fill_feed_dict(batch_data,self.embeds_placeholder, self.labels_placeholder)
		tmp = np.array(self.sess.run([self.output], feed_dict=feed_dict))
		if (not np.all(np.isfinite(tmp))):
			LOGGER.error("TFsession returned garbage")
			LOGGER.error("TFInputs"+str(eval_input)) #If it's still a problem here use tf.Print version of the graph.
		if (self.PreparedFor>eval_input.shape[0]):
			return tmp[:eval_input.shape[0]]
		return tmp

	def Save(self):
		self.summary_op =None
		self.summary_writer=None
		Instance.Save(self)
		return

	def loss_op(self, output, labels):
		diff  = tf.slice(tf.sub(output, labels),[0,self.outshape[0]-3],[-1,-1])
		# this only compares direct displacement predictions.
		loss = tf.nn.l2_loss(diff)
		tf.add_to_collection('losses', loss)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), loss

	def train_step(self,step):
		Ncase_train = self.TData.NTrainCasesInScratch()
		start_time = time.time()
		train_loss =  0.0
		total_correct = 0
		for ministep in range (0, int(Ncase_train/self.batch_size)):
			batch_data=self.PrepareData(self.TData.GetTrainBatch(self.element,  self.batch_size)) #advances the case pointer in TData...
			feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			_, total_loss_value, loss_value = self.sess.run([self.train_op, self.total_loss, self.loss], feed_dict=feed_dict)
			train_loss = train_loss + loss_value
		duration = time.time() - start_time
		#self.print_training(step, train_loss, total_correct, Ncase_train, duration)
		self.print_training(step, train_loss, Ncase_train, duration)
		return

	def test(self, step):
		Ncase_test = self.TData.NTestCasesInScratch()
		test_loss =  0.0
		test_start_time = time.time()
		#for ministep in range (0, int(Ncase_test/self.batch_size)):
		batch_data=self.PrepareData(self.TData.GetTestBatch(self.element,  self.batch_size))#, ministep)
		feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
		preds, total_loss_value, loss_value  = self.sess.run([self.output, self.total_loss,  self.loss],  feed_dict=feed_dict)
		self.TData.EvaluateTestBatch(batch_data[1],preds, self.tformer)
		test_loss = test_loss + loss_value
		duration = time.time() - test_start_time
		LOGGER.info("testing...")
		self.print_training(step, test_loss,  Ncase_test, duration)
		return test_loss, feed_dict

	def PrepareData(self, batch_data):

		#for i in range(self.batch_size):
		#	ds=GRIDS.Rasterize(batch_data[0][i])
		#	GridstoRaw(ds, GRIDS.NPts, "Inp"+str(i))

		if (batch_data[0].shape[0]==self.batch_size):
			batch_data=[batch_data[0].reshape(batch_data[0].shape[0],GRIDS.NGau,GRIDS.NGau,GRIDS.NGau,1), batch_data[1]]
		elif (batch_data[0].shape[0] < self.batch_size):
			LOGGER.info("Resizing... ")
			batch_data=[batch_data[0].resize(self.batch_size,GRIDS.NGau,GRIDS.NGau,GRIDS.NGau,1), batch_data[1].resize((self.batch_size,  batch_data[1].shape[1]))]
#			batch_data=[batch_data[0], batch_data[1].reshape((batch_data[1].shape[0],1))]
#			tmp_input = np.copy(batch_data[0])
#			tmp_output = np.copy(batch_data[1])
#			tmp_input.resize((self.batch_size,  batch_data[0].shape[1]))
#			tmp_output.resize((self.batch_size,  batch_data[1].shape[1]))
#			batch_data=[ tmp_input, tmp_output]
		return batch_data


class Instance_KRR(Instance):
	def __init__(self, TData_, ele_ = 1 , Name_=None):
		Instance.__init__(self, TData_, ele_, Name_)
		self.NetType = "KRR"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name
		self.krr = None
		return

	def evaluate(self, eval_input):
		return self.krr.predict(eval_input)

	def Save(self):
		self.summary_op =None
		self.summary_writer=None
		return

	def train(self,n_step):
		from sklearn.kernel_ridge import KernelRidge
		self.krr = KernelRidge(alpha=0.001, kernel='rbf')
		# Here we should use as much data as the kernel method can actually take.
		# probly on the order of 100k cases.
		ti,to = self.TData.GetTrainBatch(self.element,  10000)
		self.krr.fit(ti,to)
		self.test(0)
		return

	def test(self, step):
		Ncase_test = self.TData.NTestCasesInScratch()
		test_loss =  0.0
		ti,to = self.TData.GetTestBatch(self.element,  self.batch_size)
		preds  = self.krr.predict(ti)
		self.TData.EvaluateTestBatch(to,preds, self.tformer)
		return None, None

	def basis_opt_run(self):
		from sklearn.kernel_ridge import KernelRidge
		self.krr = KernelRidge(alpha=0.001, kernel='rbf')
		# Here we should use as much data as the kernel method can actually take.
		# probly on the order of 100k cases.
		ti,to = self.TData.GetTrainBatch(self.element,  10000)
		self.krr.fit(ti,to)
		Ncase_test = self.TData.NTestCasesInScratch()
		test_loss =  0.0
		ti,to = self.TData.GetTestBatch(self.element,  10000)
		preds = self.krr.predict(ti)
		return self.TData.EvaluateTestBatch(to,preds, self.tformer, Opt=True)

	def PrepareData(self, batch_data):
		raise Exception("NYI")
		return

class Queue_Instance:
	"""
	Manages a persistent training network instance
	"""
	def __init__(self, TData_, TestData_, ele_ = 1 , Name_=None, NetType_=None):
		"""
		Args:
			TData_: a TensorData
			ele_: an element type for this instance.
			Name_ : a name for this instance, attempts to load from checkpoint.
		"""
		# The tensorflow objects go up here.
		self.inshape = None
		self.outshape = None
		self.sess = None
		self.loss = None
		self.output = None
		self.train_op = None
		self.total_loss = None
		self.embeds_placeholder = None
		self.labels_placeholder = None
		self.saver = None
		self.gradient =None
		self.summary_op =None
		self.summary_writer=None
		# The parameters below belong to tensorflow and its graph
		# all tensorflow variables cannot be pickled they are populated by Prepare
		self.PreparedFor=0

		try:
			self.tf_prec
		except:
			self.tf_prec = eval(PARAMS["tf_prec"])
		self.HiddenLayers = PARAMS["HiddenLayers"]
		self.hidden1 = PARAMS["hidden1"]
		self.hidden2 = PARAMS["hidden2"]
		self.hidden3 = PARAMS["hidden3"]
		self.learning_rate = PARAMS["learning_rate"]
		self.momentum = PARAMS["momentum"]
		self.max_steps = PARAMS["max_steps"]
		self.batch_size = PARAMS["batch_size"]
		self.activation_function_type = PARAMS["NeuronType"]
		self.activation_function = None
		self.AssignActivation()

		self.path='./networks/'
		if (Name_ !=  None):
			self.name = Name_
			#self.QueryAvailable() # Should be a sanity check on the data files.
			self.Load() # Network still cannot be used until it is prepared.
			LOGGER.info("raised network: "+self.train_dir)
			return

		self.element = ele_
		self.TData = TData_
		self.TestData = TestData_
		# self.tformer = Transformer(PARAMS["InNormRoutine"], PARAMS["OutNormRoutine"], self.element, self.TData.dig.name, self.TData.dig.OType)
		if (not os.path.isdir(self.path)):
			os.mkdir(self.path)
		self.chk_file = ''

		LOGGER.info("self.learning_rate: "+str(self.learning_rate))
		LOGGER.info("self.batch_size: "+str(self.batch_size))
		LOGGER.info("self.max_steps: "+str(self.max_steps))

		self.NetType = "fc_sqdiff_queue"
		self.name = self.TData.name+"_"+self.TData.dig.name+"_"+self.NetType+"_"+str(self.element)
		self.train_dir = './networks/'+self.name
		if (self.element != 0):
			# self.TData.LoadElementToScratch(self.element, self.tformer)
			# self.tformer.Print()
			# self.TData.PrintStatus()
			self.inshape = self.TData.dig.eshape
			self.outshape = self.TData.dig.lshape
		return

	def __del__(self):
		if (self.sess != None):
			self.sess.close()
		self.Clean()

	def AssignActivation(self):
		LOGGER.debug("Assigning Activation... %s", PARAMS["NeuronType"])
		try:
			if self.activation_function_type == "relu":
				self.activation_function = tf.nn.relu
			elif self.activation_function_type == "elu":
				self.activation_function = tf.nn.elu
			elif self.activation_function_type == "selu":
				self.activation_function = self.selu
			elif self.activation_function_type == "softplus":
				self.activation_function = tf.nn.softplus
			elif self.activation_function_type == "tanh":
				self.activation_function = tf.tanh
			elif self.activation_function_type == "sigmoid":
				self.activation_function = tf.sigmoid
			else:
				print ("unknown activation function, set to relu")
				self.activation_function = tf.nn.relu
		except Exception as Ex:
			print(Ex)
			print ("activation function not assigned, set to relu")
			self.activation_function = tf.nn.relu
		return

	def evaluate(self, eval_input):
		# Check sanity of input
		if (not np.all(np.isfinite(eval_input))):
			LOGGER.error("WTF, you trying to feed me, garbage?")
			raise Exception("bad digest.")
		if (self.PreparedFor < eval_input.shape[0]):
			self.Prepare(eval_input, eval_input.shape[0])
		return

	def Prepare(self, eval_input, Ncase=1250):
		"""
		Called if only evaluations are being done, by evaluate()
		"""
		self.Clean()
		self.AssignActivation()
		# Always prepare for at least 125,000 cases which is a 50x50x50 grid.
		eval_labels = np.zeros(Ncase)  # dummy labels
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.placeholder_inputs(Ncase)
			self.output = self.inference(self.embeds_placeholder)
			self.saver = tf.train.Saver()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			metafiles = [x for x in os.listdir(self.train_dir) if (x.count('meta')>0)]
			if (len(metafiles)>0):
				most_recent_meta_file=metafiles[0]
				LOGGER.debug("Restoring training from Meta file: "+most_recent_meta_file)
				config = tf.ConfigProto(allow_soft_placement=True)
				self.sess = tf.Session(config=config)
				self.saver = tf.train.import_meta_graph(self.train_dir+'/'+most_recent_meta_file)
				self.saver.restore(self.sess, tf.train.latest_checkpoint(self.train_dir))
		self.PreparedFor = Ncase
		return

	def Clean(self):
		if (self.sess != None):
			self.sess.close()
		self.sess = None
		self.loss = None
		self.output = None
		self.total_loss = None
		self.train_op = None
		self.embeds_placeholder = None
		self.labels_placeholder = None
		self.saver = None
		self.gradient =None
		self.summary_writer = None
		self.PreparedFor = 0
		self.summary_op = None
		self.activation_function = None
		self.coord = None
		self.threads = None
		return

	def SaveAndClose(self):
		print("Saving TFInstance...")
		if (self.TData!=None):
			self.TData.CleanScratch()
		self.Clean()
		#print("Going to pickle...\n",[(attr,type(ins)) for attr,ins in self.__dict__.items()])
		f=open(self.path+self.name+".tfn","wb")
		pickle.dump(self.__dict__, f, protocol=pickle.HIGHEST_PROTOCOL)
		f.close()
		return

	def variable_summaries(self, var):
		"""Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
		with tf.name_scope('summaries'):
			mean = tf.reduce_mean(var)
			tf.summary.scalar('mean', mean)
		with tf.name_scope('stddev'):
			stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
			tf.summary.scalar('stddev', stddev)
			tf.summary.scalar('max', tf.reduce_max(var))
			tf.summary.scalar('min', tf.reduce_min(var))
			tf.summary.histogram('histogram', var)

	# one of these two routines need to be removed I think. -JAP
	def save_chk(self,  step, feed_dict=None):  # this can be included in the Instance
		#cmd="rm  "+self.train_dir+"/"+self.name+"-chk-*"
		#os.system(cmd)
		checkpoint_file_mini = os.path.join(self.train_dir,self.name+'-chk-'+str(step))
		LOGGER.info("Saving Checkpoint file, "+checkpoint_file_mini)
		self.saver.save(self.sess, checkpoint_file_mini)
		return

	#this isn't really the correct way to load()
	# only the local class members (not any TF objects should be unpickled.)
	def Load(self):
		LOGGER.info("Unpickling TFInstance...")
		f = open(self.path+self.name+".tfn","rb")
		import TensorMol.PickleTM
		tmp = TensorMol.PickleTM.UnPickleTM(f)
		self.Clean()
		# All this shit should be deleteable after re-training.
		self.__dict__.update(tmp)
		f.close()
		chkfiles = [x for x in os.listdir(self.train_dir) if (x.count('chk')>0 and x.count('meta')==0)]
		if (len(chkfiles)>0):
			self.chk_file = chkfiles[0]
		else:
			LOGGER.error("Network not found... Traindir:"+self.train_dir)
			LOGGER.error("Traindir contents: "+str(os.listdir(self.train_dir)))
		return

	def _variable_with_weight_decay(self, var_name, var_shape, var_stddev, var_wd):
		"""Helper to create an initialized Variable with weight decay.

		Note that the Variable is initialized with a truncated normal distribution.
		A weight decay is added only if one is specified.

		Args:
		name: name of the variable
		shape: list of ints
		stddev: standard deviation of a truncated Gaussian
		wd: add L2Loss weight decay multiplied by this float. If None, weight
		decay is not added for this Variable.

		Returns:
		Variable Tensor
		"""
		var = tf.Variable(tf.truncated_normal(var_shape, stddev=var_stddev, dtype=self.tf_prec), name=var_name)
		if var_wd is not None:
			try:
				weight_decay = tf.multiply(tf.nn.l2_loss(var), var_wd, name='weight_loss')
			except:
				print("tf.mul() is deprecated in tensorflow 1.0 in favor of tf.multiply(). Please upgrade soon.")
				weight_decay = tf.mul(tf.nn.l2_loss(var), var_wd, name='weight_loss')
			tf.add_to_collection('losses', weight_decay)
		return var

	# def placeholder_inputs(self, batch_size):
	# 	raise("Populate placeholder_inputs")
	# 	return

	# def fill_feed_dict(self, batch_data, embeds_pl, labels_pl):
	# 	"""Fills the feed_dict for training the given step.
	# 	A feed_dict takes the form of:
	# 	feed_dict = {
	# 	<placeholder>: <tensor of values to be passed for placeholder>,
	# 	....
	# 	}
	# 	Args:
	# 	data_set: The set of images and labels, from input_data.read_data_sets()
	# 	embeds_pl: The images placeholder, from placeholder_inputs().
	# 	labels_pl: The labels placeholder, from placeholder_inputs().
	# 	Returns:
	# 	feed_dict: The feed dictionary mapping from placeholders to values.
	# 	"""
	# 	# Don't eat shit.
	# 	if (not np.all(np.isfinite(batch_data[0]))):
	# 		LOGGER.error("I was fed shit")
	# 		raise Exception("DontEatShit")
	# 	if (not np.all(np.isfinite(batch_data[1]))):
	# 		LOGGER.error("I was fed shit")
	# 		raise Exception("DontEatShit")
	# 	feed_dict = {embeds_pl: batch_data[0], labels_pl: batch_data[1],}
	# 	return feed_dict

	def inference(self, inputs):
		"""Builds the network architecture. Number of hidden layers and nodes in each layer defined in TMParams "HiddenLayers".
		Args:
			inputs: input placeholder for training data from Digester.
		Returns:
			output: scalar or vector of OType from Digester.
		"""
		hiddens = []
		for i in range(len(self.HiddenLayers)):
			if i == 0:
				with tf.name_scope('hidden1'):
					weights = self._variable_with_weight_decay(var_name='weights',
									var_shape=(self.inshape+[self.HiddenLayers[i]]),
									var_stddev= 1.0 / math.sqrt(float(self.inshape[0])), var_wd= 0.00)
					biases = tf.Variable(tf.zeros([self.HiddenLayers[i]], dtype=self.tf_prec), name='biases')
					hiddens.append(self.activation_function(tf.matmul(inputs, weights) + biases))
					# tf.scalar_summary('min/' + weights.name, tf.reduce_min(weights))
					# tf.histogram_summary(weights.name, weights)
			else:
				with tf.name_scope('hidden'+str(i+1)):
					weights = self._variable_with_weight_decay(var_name='weights',
									var_shape=[self.HiddenLayers[i-1], self.HiddenLayers[i]],
									var_stddev= 1.0 / math.sqrt(float(self.HiddenLayers[i-1])), var_wd= 0.00)
					biases = tf.Variable(tf.zeros([self.HiddenLayers[i]], dtype=self.tf_prec),name='biases')
					hiddens.append(self.activation_function(tf.matmul(hiddens[-1], weights) + biases))
		with tf.name_scope('regression_linear'):
			weights = self._variable_with_weight_decay(var_name='weights',
							var_shape=[self.HiddenLayers[-1]]+self.outshape,
							var_stddev= 1.0 / math.sqrt(float(self.HiddenLayers[-1])), var_wd= 0.00)
			biases = tf.Variable(tf.zeros(self.outshape, dtype=self.tf_prec), name='biases')
			output = tf.matmul(hiddens[-1], weights) + biases
		return output

	def loss_op(self, output, labels):
		diff  = tf.subtract(output, labels)
		loss = tf.nn.l2_loss(diff)
		tf.add_to_collection('losses', loss)
		return tf.add_n(tf.get_collection('losses'), name='total_loss'), loss

	def training(self, loss, learning_rate, momentum):
		"""Sets up the training Ops.
		Creates a summarizer to track the loss over time in TensorBoard.
		Creates an optimizer and applies the gradients to all trainable variables.
		The Op returned by this function is what must be passed to the
		`sess.run()` call to cause the model to train.
		Args:
		loss: Loss tensor, from loss().
		learning_rate: The learning rate to use for gradient descent.
		Returns:
		train_op: The Op for training.
		"""
		tf.summary.scalar(loss.op.name, loss)
		optimizer = tf.train.AdamOptimizer(learning_rate)
		#optimizer = tf.train.MomentumOptimizer(learning_rate, momentum)
		global_step = tf.Variable(0, name='global_step', trainable=False)
		train_op = optimizer.minimize(loss, global_step=global_step)
		return train_op

	def train(self, mxsteps, continue_training= False):
		self.TrainPrepare(continue_training)
		test_freq = PARAMS["test_freq"]
		mini_test_loss = 100000000 # some big numbers
		self.coord = tf.train.Coordinator()
		self.threads = tf.train.start_queue_runners(sess=self.sess, coord=self.coord)
		try:
			step = 0
			while not self.coord.should_stop():
				self.train_step(step)
				if step%test_freq==0 and step!=0 :
					test_loss = self.test(step)
					if (test_loss < mini_test_loss):
						mini_test_loss = test_loss
						self.save_chk(step)
				step += 1
		except tf.errors.OutOfRangeError:
			print('Done training -- epoch limit reached')
		finally:
			self.coord.request_stop()
			self.coord.join(self.threads)
			self.SaveAndClose()
		return

	def train_step(self,step):
		Ncase_train = self.TData.SamplesPerElement[self.element]
		start_time = time.time()
		train_loss =  0.0
		total_correct = 0
		for ministep in range (0, int(Ncase_train/self.batch_size)):
			# batch_data=self.TData.GetTrainBatch(self.element,  self.batch_size) #advances the case pointer in TData...
			# feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
			_, total_loss_value, loss_value = self.sess.run([self.train_op, self.total_loss, self.loss])
			train_loss = train_loss + loss_value
		duration = time.time() - start_time
		#self.print_training(step, train_loss, total_correct, Ncase_train, duration)
		self.print_training(step, train_loss, Ncase_train, duration)
		return


	def TrainPrepare(self,  continue_training =False):
		"""Train for a number of steps."""
		with tf.Graph().as_default():
			self.embeds_placeholder, self.labels_placeholder = self.inputs()
			self.output = self.inference(self.embeds_placeholder)
			self.total_loss, self.loss = self.loss_op(self.output, self.labels_placeholder)
			self.train_op = self.training(self.total_loss, self.learning_rate, self.momentum)
			self.summary_op = tf.summary.merge_all()
			init = tf.group(tf.global_variables_initializer(),tf.local_variables_initializer())
			self.saver = tf.train.Saver()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			self.sess.run(init)
			try: # I think this may be broken
				chkfiles = [x for x in os.listdir(self.train_dir) if (x.count('chk')>0 and x.count('meta')==0)]
				metafiles = [x for x in os.listdir(self.train_dir) if (x.count('meta')>0)]
				if (len(metafiles)>0):
					most_recent_meta_file=metafiles[0]
					print("Restoring training from Metafile: ",most_recent_meta_file)
					#Set config to allow soft device placement for temporary fix to known issue with Tensorflow up to version 0.12 atleast - JEH
					config = tf.ConfigProto(allow_soft_placement=True)
					self.sess = tf.Session(config=config)
					self.saver = tf.train.import_meta_graph(self.train_dir+'/'+most_recent_meta_file)
					self.saver.restore(self.sess, tf.train.latest_checkpoint(self.train_dir))
			except Exception as Ex:
				print("Restore Failed",Ex)
				pass
			self.summary_writer =  tf.summary.FileWriter(self.train_dir, self.sess.graph)
			return

	def test(self, step):
		Ncase_test = self.TestData.SamplesPerElement[self.element]
		test_loss =  0.0
		test_start_time = time.time()
		#for ministep in range (0, int(Ncase_test/self.batch_size)):
		# batch_data=self.TData.GetTestBatch(self.element,  self.batch_size)#, ministep)
		# feed_dict = self.fill_feed_dict(batch_data, self.embeds_placeholder, self.labels_placeholder)
		preds, total_loss_value, loss_value  = self.sess.run([self.output, self.total_loss,  self.loss])
		# self.TData.EvaluateTestBatch(batch_data[1],preds, self.tformer)
		test_loss = test_loss + loss_value
		duration = time.time() - test_start_time
		print("testing...")
		self.print_training(step, test_loss,  Ncase_test, duration, Train=False)
		return test_loss

	def print_training(self, step, loss, Ncase, duration, Train=True):
		denom = max((int(Ncase/self.batch_size)),1)
		if Train:
			LOGGER.info("step: %7d  duration: %.5f train loss: %.10f", step, duration,(float(loss)/(denom*self.batch_size)))
		else:
			LOGGER.info("step: %7d  duration: %.5f test loss: %.10f", step, duration,(float(loss)/(denom*self.batch_size)))
		return

	def read_and_decode(self, filename_queue):
		reader = tf.TFRecordReader()
		_, serialized_example = reader.read(filename_queue)
		features = tf.parse_single_example(
			serialized_example,
			# Defaults are not specified since both keys are required.
			features={
				'input_raw': tf.FixedLenFeature([], tf.string),
				'label_raw': tf.FixedLenFeature([], tf.string),
			})
		inputs = tf.decode_raw(features['input_raw'], tf.float32)
		inputs.set_shape(self.inshape)
		label = tf.decode_raw(features['label_raw'], tf.float32)
		label.set_shape(self.outshape)
		return inputs, label

	def inputs(self, test_=False):
		"""Reads input data num_epochs times.
		Args:
		train: Selects between the training (True) and validation (False) data.
		batch_size: Number of examples per returned batch.
		num_epochs: Number of times to read the input data, or 0/None to
			train forever.
		Returns:
		A tuple (images, labels), where:
		* images is a float tensor with shape [batch_size, mnist.IMAGE_PIXELS]
			in the range [-0.5, 0.5].
		* labels is an int32 tensor with shape [batch_size] with the true label,
			a number in the range [0, mnist.NUM_CLASSES).
		Note that an tf.train.QueueRunner is added to the graph, which
		must be run using e.g. tf.train.start_queue_runners().
		"""
		num_epochs = self.max_steps
		if test_:
			filename = os.path.join(
				self.TestData.AvailableDataFiles[self.element])
		else:
			filename = os.path.join(
				self.TData.AvailableDataFiles[self.element])

		with tf.name_scope('input'):
			filename_queue = tf.train.string_input_producer(
							[filename], num_epochs=num_epochs, shuffle=True)
			# Even when reading in multiple threads, share the filename
			# queue.
			inputs, label = self.read_and_decode(filename_queue)
			# Shuffle the examples and collect them into batch_size batches.
			# (Internally uses a RandomShuffleQueue.)
			# We run this in two threads to avoid being a bottleneck.
			input_batch, label_batch = tf.train.shuffle_batch(
				[inputs, label], batch_size=self.batch_size, num_threads=8,
				capacity = 5*self.batch_size,
				# Ensures a minimum amount of shuffling of examples.
				min_after_dequeue = 2*self.batch_size)
			return input_batch, label_batch
