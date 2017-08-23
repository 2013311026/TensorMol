"""
Linear Scaling Atom Neighbor List Generators.
see also: http://scipy-cookbook.readthedocs.io/items/KDTree_example.html
Depending on cutoffs and density these scale to >20,000 atoms
"""

from __future__ import absolute_import
from __future__ import print_function
import numpy as np
#from PairProviderTF import *
from MolEmb import Make_NListNaive, Make_NListLinear

#
# I excised the K-D tree because it had some weird bugs.
# we will have to do our own Octree implementation sometime.
# for now I just coded the naive (quadratic) thing in C++ and seems fast enough IMHO.
# JAP
#

class NeighborList:
	"""
	TODO: incremental tree and neighborlist updates.
	"""
	def __init__(self, x_, DoTriples_ = False, DoPerms_ = False, ele_ = None, alg_ = None, sort_ = False):
		"""
		Builds or updates a neighbor list of atoms within rcut_
		using n*Log(n) kd-tree.

		Args:
			x_: coordinate array
			rcut_: distance cutoff.
			ele_: element types of each atoms.
			sort_: whether sorting the jk in triples by atom index
		"""
		self.natom = x_.shape[0] # includes periodic images.
		self.x = x_.T.copy()
		self.pairs = None
		self.triples = None
		self.DoTriples = DoTriples_
		self.DoPerms = DoPerms_
		self.ele = ele_
		self.npairs = None
		self.ntriples = None
		self.alg = alg_
		self.sort = sort_
		return

	def Update(self, x_, rcut_pairs=5.0, rcut_triples=5.0, molind_ = None, nreal_ = None):
		"""
		In the future this should only force incremental builds.

		Args:
			x_: coordinates.
			rcut_: cutoff of the force.
			molind_: possible molecule index if we are doing a set.
			nreal_: only generate pairs for the first nreal_ atoms.
		"""
		self.x = x_.copy()
		if (self.DoTriples):
			self.pairs, self.triples = self.buildPairsAndTriples(rcut_pairs,rcut_triples,molind_)
			self.npairs = self.pairs.shape[0]
			self.ntriples = self.triples.shape[0]
		else:
			self.pairs = self.buildPairs(rcut_pairs,molind_,nreal_)
			self.npairs = self.pairs.shape[0]
		return

	def buildPairs(self, rcut=5.0, molind_=None, nreal_=None):
		"""
		Returns the nonzero pairs, triples in self.x within the cutoff.
		Triples are non-repeating ie: no 1,2,2 or 2,2,2 etc. but unordered

		Args:
			rcut: the cutoff for pairs and triples
		Returns:
			pair matrix (npair X 2)
			triples matrix (ntrip X 3)
		"""
		pair = []
		ntodo = self.natom
		if (nreal_ != None):
			ntodo = nreal_
		pair = None
		if (self.alg==0):
			pair = Make_NListNaive(self.x,rcut,ntodo,int(self.DoPerms))
		else:
			pair = Make_NListLinear(self.x,rcut,ntodo,int(self.DoPerms))
		npairi = map(len,pair)
		npair = sum(npairi)
		p = None
		if (molind_!=None):
			p=np.zeros((npair,3),dtype = np.uint64)
		else:
			p=np.zeros((npair,2),dtype = np.uint64)
		pp = 0
		for i in range(ntodo):
			for j in pair[i]:
				if (molind_!=None):
					p[pp,0]=molind_
					p[pp,1]=i
					p[pp,2]=j
				else:
					p[pp,0]=i
					p[pp,1]=j
				pp = pp+1
		del pair
		return p

	def buildPairsAndTriples(self, rcut_pairs=5.0, rcut_triples=5.0, molind_=None, nreal_=None):
		"""
		Returns the nonzero pairs, triples in self.x within the cutoff.
		Triples are non-repeating ie: no 1,2,2 or 2,2,2 etc. but unordered

		Args:
			rcut: the cutoff for pairs and triples
		Returns:
			pair matrix (npair X 2)
			triples matrix (ntrip X 3)
		"""
		if (self.ele is None):
			print("WARNING... need self.ele for angular SymFunc triples... ")
		pair = []
		tpair = [] # since these may have different cutoff
		ntodo = self.natom
		if (nreal_ != None):
			ntodo = nreal_
		pair = None
		tpair = None

		# this works...
		#print "TEST"
		#pair = Make_NListNaive(self.x,rcut_pairs,ntodo)
		#print pair
		#pair = Make_NListLinear(self.x,rcut_pairs,ntodo)
		#print pair
		#print "~~TEST"

		if (self.alg==0):
			pair = Make_NListNaive(self.x,rcut_pairs,ntodo,int(self.DoPerms))
			tpair = Make_NListNaive(self.x,rcut_triples,ntodo,int(self.DoPerms))
		else:
			pair = Make_NListLinear(self.x,rcut_pairs,ntodo,int(self.DoPerms))
			tpair = Make_NListLinear(self.x,rcut_triples,ntodo,int(self.DoPerms))
		npairi = map(len,pair)
		npair = sum(npairi)
		npairi = map(len,tpair)
		#ntrip = sum(map(lambda x: x*x if x>0 else 0, npairi))
		ntrip = sum(map(lambda x: x*(x-1)/2 if x>0 else 0, npairi))
		p = None
		t = None
		if (molind_!=None):
			p=np.zeros((npair,3),dtype = np.uint64)
			t=np.zeros((ntrip,4),dtype = np.uint64)
		else:
			p=np.zeros((npair,2),dtype = np.uint64)
			t=np.zeros((ntrip,3),dtype = np.uint64)
		pp = 0
		tp = 0
		for i in range(ntodo):
			for j in pair[i]:
				if (molind_!=None):
					p[pp,0]=molind_
					p[pp,1]=i
					p[pp,2]=j
				else:
					p[pp,0]=i
					p[pp,1]=j
				pp = pp+1
			for j in tpair[i]:
				for k in tpair[i]:
					#if True:
					if (k > j): # do not do ijk, ikj permutation
					#if (k!=j):
						if (molind_!=None):
							t[tp,0]=molind_
							t[tp,1]=i
							if self.ele is not None and self.ele[j] > self.ele[k]:  # atom will smaller element index alway go first
								t[tp,2]=k
								t[tp,3]=j
							elif self.sort and j > k:
								t[tp,2]=k
								t[tp,3]=j
							else:
								t[tp,2]=j
								t[tp,3]=k
						else:
							t[tp,0]=i
							if self.ele is not None and self.ele[j] > self.ele[k]:
								t[tp,1]=k
								t[tp,2]=j
							elif self.sort and j > k:
								t[tp,1]=k
								t[tp,2]=j
							else:
								t[tp,1]=j
								t[tp,2]=k
						tp=tp+1
		del pair
		del tpair
		return p,t

class NeighborListSet:
	def __init__(self, x_, nnz_, DoTriples_=False, DoPerms_=False, ele_=None, alg_ = None, sort_ = False):
		"""
		A neighborlist for a set

		Args:
			x_: NMol X MaxNAtom X 3 tensor of coordinates.
			nnz_: NMol vector of maximum atoms in each mol.
			ele_: element type of each atom.
			sort_: whether sort jk in triples by atom index 
		"""
		self.nlist = []
		self.nmol = x_.shape[0]
		self.maxnatom = x_.shape[1]
		self.alg = 0 if self.maxnatom < 500 else 1
		if (alg_ != None):
			self.alg = alg_
		# alg=0 naive quadratic.
		# alg=1 linear scaling
		# alg=2 PairProvider.
		self.x = x_
		self.nnz = nnz_
		self.ele = ele_
		self.sort = sort_
		self.pairs = None
		self.DoTriples = DoTriples_
		self.DoPerms = DoPerms_
		self.triples = None
		self.UpdateInterval = 1
		self.UpdateCounter = 0
		self.PairMaker=None
		if (self.alg<2):
			if self.ele is None:
				for i in range(self.nmol):
					self.nlist.append(NeighborList(x_[i,:nnz_[i]],DoTriples_,DoPerms_, None, self.alg, self.sort))
			else:
				for i in range(self.nmol):
					self.nlist.append(NeighborList(x_[i,:nnz_[i]],DoTriples_,DoPerms_, self.ele[i,:nnz_[i]], self.alg, self.sort))
		else:
			self.PairMaker = PairProvider(self.nmol,self.maxnatom)
		return

	def Update(self, x_, rcut_pairs = 5.0, rcut_triples = 5.0):
		if (self.UpdateCounter == 0):
			self.UpdateCounter = self.UpdateCounter + 1
			self.x = x_.copy()
			if (self.DoTriples):
				self.pairs, self.triples = self.buildPairsAndTriples(rcut_pairs,rcut_triples)
			else:
				self.pairs = self.buildPairs(rcut_pairs)
		elif (self.UpdateCounter < self.UpdateInterval):
			self.UpdateCounter = self.UpdateCounter + 1
		else:
			self.UpdateCounter = 0

	def buildPairs(self, rcut=5.0):
		"""
		builds nonzero pairs and triples for current x.

		Args:
			rcut_: a cutoff parameter.
		Returns:
			(nnzero pairs X 3 pair tensor) (mol , I , J)
		"""
		if self.alg < 2:
			for i,mol in enumerate(self.nlist):
				mol.Update(self.x[i,:self.nnz[i]],rcut,rcut,i)
		else:
			return self.PairMaker(self.x,rcut,self.nnz)
		nzp = sum([mol.npairs for mol in self.nlist])
		trp = np.zeros((nzp,3),dtype=np.uint64)
		pp = 0
		for mol in self.nlist:
			trp[pp:pp+mol.npairs] = mol.pairs
			pp += mol.npairs
		return trp

	def buildPairsAndTriples(self, rcut_pairs=5.0, rcut_triples=5.0):
		"""
		builds nonzero pairs and triples for current x.

		Args:
			rcut_: a cutoff parameter.
		Returns:
			(nnzero pairs X 3 pair tensor) (mol , I , J)
			(nnzero X 4 triples tensor) (mol , I , J , K)
		"""
		if (self.alg==2):
			trp = self.PairMaker(self.x,rcut_pairs,self.nnz)
			trtmp = self.PairMaker(self.x,rcut_triples,self.nnz)
			hack=[[[] for j in range(self.maxnatom)] for i in range(self.nmol)]
			tore = []
			for p in trtmp:
				(hack[p[0]])[p[1]].append(p[2])
			for i in range(self.nmol):
				for j in range(self.maxnatom):
					for k in hack[i][j]:
						tore.append([i,j,k])
			return trp, np.array(tore)
		else:
			for i,mol in enumerate(self.nlist):
				mol.Update(self.x[i,:self.nnz[i]],rcut_pairs,rcut_triples,i)
			nzp = sum([mol.npairs for mol in self.nlist])
			nzt = sum([mol.ntriples for mol in self.nlist])
			trp = np.zeros((nzp,3),dtype=np.uint64)
			trt = np.zeros((nzt,4),dtype=np.uint64)
			pp = 0
			tp = 0
			for mol in self.nlist:
				trp[pp:pp+mol.npairs] = mol.pairs
				trt[tp:tp+mol.ntriples] = mol.triples
				pp += mol.npairs
				tp += mol.ntriples
			return trp, trt

	def buildPairsAndTriplesWithEleIndex(self, rcut_pairs=5.0, rcut_triples=5.0, ele=None, elep=None):
		"""
		generate sorted pairs and triples with index of correspoding ele or elepair append to it.
		sorted order: mol, i (center atom), l (ele or elepair index), j (connected atom 1), k (connected atom 2 for triples)

		Args:
			rcut_: a cutoff parameter.
			ele: element
			elep: element pairs
		Returns:
			(nnzero pairs X 4 pair tensor) (mol, I, J, L)
			(nnzero triples X 5 triple tensor) (mol, I, J, K, L) 
		"""
	
		if not self.sort:
			print ("Warning! Triples need to be sorted")
		if self.ele == None:	
			raise Exception("Element type of each atom is needed.")
		#import time
		#t0 = time.time()
		trp, trt = self.buildPairsAndTriples(rcut_pairs, rcut_triples)
		#print ("make pair and triple time:", time.time()-t0)
		#t_start = time.time()
		eleps = np.hstack((elep, np.flip(elep, axis=1))).reshape((elep.shape[0], 2, -1))
		Z = self.ele[trp[:, 0], trp[:, 2]]
		pair_mask = np.equal(Z.reshape(trp.shape[0],1,1), ele.reshape(ele.shape[0],1)) 
		pair_index = np.where(np.all(pair_mask, axis=-1))[1]
		Z1 = self.ele[trt[:, 0], trt[:, 2]]
		Z2 = self.ele[trt[:, 0], trt[:, 3]]
		Z1Z2 = np.transpose(np.vstack((Z1, Z2)))
		trip_mask = np.equal(Z1Z2.reshape((trt.shape[0],1,1,2)), eleps.reshape((eleps.shape[0],2,2)))
		trip_index = np.where(np.any(np.all(trip_mask, axis=-1),axis=-1))[1]
		trpE = np.concatenate((trp, pair_index.reshape((-1,1))), axis=-1)
		trtE = np.concatenate((trt, trip_index.reshape((-1,1))), axis=-1)
		#t0 = time.time()
		sort_index = np.lexsort((trpE[:,2], trpE[:,3], trpE[:,1], trpE[:,0]))
		trpE_sorted = trpE[sort_index]
		sort_index = np.lexsort((trtE[:,2], trtE[:,3], trtE[:,4], trtE[:,1], trtE[:,0]))
		trtE_sorted = trtE[sort_index]
		#print ("numpy lexsorting time:", time.time() -t0)
		#print ("time to append and sort element", time.time() - t_start)
		return trpE_sorted, trtE_sorted
