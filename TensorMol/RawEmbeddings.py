"""
Raw => various descriptors in Tensorflow code.

The Raw format is a batch of rank three tensors.
mol X MaxNAtoms X 4
The final dim is atomic number, x,y,z (Angstrom)

https://www.youtube.com/watch?v=h2zgB93KANE
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from TensorMol.Neighbors import *
from TensorMol.TensorData import *
from TensorMol.ElectrostaticsTF import *
from tensorflow.python.client import timeline
import numpy as np
import cPickle as pickle
import math, time, os, sys, os.path
if (HAS_TF):
	import tensorflow as tf

def AllTriples(rng):
	"""Returns all possible triples of an input list.

	Args:
		rng: a 1D integer tensor to be triply outer product'd
	Returns:
		A natom X natom X natom X 3 tensor of all triples of entries from rng.
	"""
	rshp = tf.shape(rng)
	natom = rshp[0]
	v1 = tf.tile(tf.reshape(rng,[natom,1]),[1,natom])
	v2 = tf.tile(tf.reshape(rng,[1,natom]),[natom,1])
	v3 = tf.transpose(tf.stack([v1,v2],0),perm=[1,2,0])
	# V3 is now all pairs (nat x nat x 2). now do the same with another to make nat X 3
	v4 = tf.tile(tf.reshape(v3,[natom,natom,1,2]),[1,1,natom,1])
	v5 = tf.tile(tf.reshape(rng,[1,1,natom,1]),[natom,natom,1,1])
	v6 = tf.concat([v4,v5], axis = 3) # All triples in the range.
	return v6

def AllTriplesSet(rng, prec=tf.int32):
	"""Returns all possible triples of integers between zero and natom.

	Args:
		rng: a 1D integer tensor to be triply outer product'd
	Returns:
		A Nmol X natom X natom X natom X 4 tensor of all triples.
	"""
	natom = tf.shape(rng)[1]
	nmol = tf.shape(rng)[0]
	v1 = tf.tile(tf.reshape(rng,[nmol,natom,1]),[1,1,natom])
	v2 = tf.tile(tf.reshape(rng,[nmol,1,natom]),[1,natom,1])
	v3 = tf.transpose(tf.stack([v1,v2],1),perm=[0,2,3,1])
	# V3 is now all pairs (nat x nat x 2). now do the same with another to make nat X 3
	v4 = tf.tile(tf.reshape(v3,[nmol,natom,natom,1,2]),[1,1,1,natom,1])
	v5 = tf.tile(tf.reshape(rng,[nmol,1,1,natom,1]),[1,natom,natom,1,1])
	v6 = tf.concat([v4,v5], axis = 4) # All triples in the range.
	v7 = tf.cast(tf.tile(tf.reshape(tf.range(nmol),[nmol,1,1,1,1]),[1,natom,natom,natom,1]), dtype=prec)
	v8 = tf.concat([v7,v6], axis = -1)
	return v8

def AllDoublesSet(rng, prec=tf.int32):
	"""Returns all possible triples of integers between zero and natom.

	Args:
		natom: max integer
	Returns:
		A nmol X natom X natom X 3 tensor of all doubles.
	"""
	natom = tf.shape(rng)[1]
	nmol = tf.shape(rng)[0]
	v1 = tf.tile(tf.reshape(rng,[nmol,natom,1]),[1,1,natom])
	v2 = tf.tile(tf.reshape(rng,[nmol,1,natom]),[1,natom,1])
	v3 = tf.transpose(tf.stack([v1,v2],1),perm=[0,2,3,1])
	v4 = tf.cast(tf.tile(tf.reshape(tf.range(nmol),[nmol,1,1,1]),[1,natom,natom,1]),dtype=prec)
	v5 = tf.concat([v4,v3], axis = -1)
	return v5

def AllSinglesSet(rng, prec=tf.int32):
	"""Returns all possible triples of integers between zero and natom.

	Args:
		natom: max integer
	Returns:
		A nmol X natom X 2 tensor of all doubles.
	"""
	natom = tf.shape(rng)[1]
	nmol = tf.shape(rng)[0]
	v1 = tf.reshape(rng,[nmol,natom,1])
	v2 = tf.cast(tf.tile(tf.reshape(tf.range(nmol),[nmol,1,1]),[1,natom,1]), dtype=prec)
	v3 = tf.concat([v2,v1], axis = -1)
	return v3

def ZouterSet(Z):
	"""
	Returns the outer product of atomic numbers for all molecules.

	Args:
		Z: nMol X MaxNAtom X 1 Z tensor
	Returns
		Z1Z2: nMol X MaxNAtom X MaxNAtom X 2 Z1Z2 tensor.
	"""
	zshp = tf.shape(Z)
	Zs = tf.reshape(Z,[zshp[0],zshp[1],1])
	z1 = tf.tile(Zs, [1,1,zshp[1]])
	z2 = tf.transpose(z1,perm=[0,2,1])
	return tf.transpose(tf.stack([z1,z2],axis=1),perm=[0,2,3,1])

def DifferenceVectorsSet(r_,prec = tf.float64):
	"""
	Given a nmol X maxnatom X 3 tensor of coordinates this
	returns a nmol X maxnatom X maxnatom X 3 tensor of Rij
	"""
	natom = tf.shape(r_)[1]
	nmol = tf.shape(r_)[0]
	#ri = tf.tile(tf.reshape(r_,[nmol,1,natom,3]),[1,natom,1,1])
	ri = tf.tile(tf.reshape(tf.cast(r_,prec),[nmol,1,natom*3]),[1,natom,1])
	ri = tf.reshape(ri, [nmol, natom, natom, 3])
	rj = tf.transpose(ri,perm=(0,2,1,3))
	return (ri-rj)

def DifferenceVectorsLinear(B, NZP):
	"""
	B: Nmol X NmaxNAtom X 3 coordinate tensor
	NZP: a index matrix (nzp X 3)
	"""
	Ii = tf.slice(NZP,[0,0],[-1,2])
	Ij = tf.concat([tf.slice(NZP,[0,0],[-1,1]),tf.slice(NZP,[0,2],[-1,1])],1)
	Ri = tf.gather_nd(B,Ii)
	Rj = tf.gather_nd(B,Ij)
	A = Ri - Rj
	return A
# In[150]:


def TFSymASet(R, Zs, eleps_, SFPs_, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eleps_: a nelepairs X 2 tensor of element pairs present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 4 X nzeta X neta X thetas X nRs. For example, SFPs_[0,0,0,0,0]
	    is the first zeta parameter. SFPs_[3,0,0,0,1] is the second R parameter.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	natom3 = natom*natom2
	nelep = tf.shape(eleps_)[0]
	pshape = tf.shape(SFPs_)
	nzeta = pshape[1]
	neta = pshape[2]
	ntheta = pshape[3]
	nr = pshape[4]
	nsym = nzeta*neta*ntheta*nr
	infinitesimal = 0.000000000000000000000000001
	onescalar = 1.0 - 0.0000000000000001

	# atom triples.
	ats = AllTriplesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0,0],[nmol,natom,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,0,1],[nmol,natom,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,0,2],[nmol,natom,natom,natom,1])
	Rk_inds = tf.slice(ats,[0,0,0,0,3],[nmol,natom,natom,natom,1])
	Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	Z1Z2 = ZouterSet(Zs)
	ZPairs = tf.gather_nd(Z1Z2,Rjk_inds) # should have shape nmol X natom3 X 2
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom3,1,2]),tf.reshape(eleps_,[1,1,nelep,2])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.logical_and(tf.not_equal(Ri_inds,Rj_inds),tf.not_equal(Ri_inds,Rk_inds)),[nmol,natom3,1]),[1,1,nelep])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.range(nelep)
	ats = tf.tile(tf.reshape(ats,[nmol,natom3,1,4]),[1,1,nelep,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nelep,1]),[nmol,natom3,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom3 * nelep X 5 (mol, i,j,k,l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	miks = tf.concat([tf.slice(GoodInds,[0,0],[nnz,2]),tf.slice(GoodInds,[0,3],[nnz,1])],axis=-1)
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	B = tf.gather_nd(Rij,miks)
	RijRik = tf.reduce_sum(A*B,axis=1)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)
	RikRik = tf.sqrt(tf.reduce_sum(B*B,axis=1)+infinitesimal)
	denom = RijRij*RikRik+infinitesimal
	# Mask any troublesome entries.
	ToACos = RijRik/denom
	ToACos = tf.where(tf.greater_equal(ToACos,1.0),tf.ones_like(ToACos, dtype=prec)*onescalar,ToACos)
	ToACos = tf.where(tf.less_equal(ToACos,-1.0),-1.0*tf.ones_like(ToACos, dtype=prec)*onescalar,ToACos)
	Thetaijk = tf.acos(ToACos)
	zetatmp = tf.cast(tf.reshape(SFPs_[0],[1,nzeta,neta,ntheta,nr]),prec)
	thetatmp = tf.cast(tf.tile(tf.reshape(SFPs_[2],[1,nzeta,neta,ntheta,nr]),[nnz,1,1,1,1]),prec)
	# Broadcast the thetas and ToCos together
	tct = tf.tile(tf.reshape(Thetaijk,[nnz,1,1,1,1]),[1,nzeta,neta,ntheta,nr])
	ToCos = tct-thetatmp
	Tijk = tf.cos(ToCos) # shape: natom3 X ...
	# complete factor 1
	fac1 = tf.pow(tf.cast(2.0, prec),1.0-zetatmp)*tf.pow((1.0+Tijk),zetatmp)
	etmp = tf.cast(tf.reshape(SFPs_[1],[1,nzeta,neta,ntheta,nr]),prec) # ijk X zeta X eta ....
	rtmp = tf.cast(tf.reshape(SFPs_[3],[1,nzeta,neta,ntheta,nr]),prec) # ijk X zeta X eta ....
	ToExp = ((RijRij+RikRik)/2.0)
	tet = tf.tile(tf.reshape(ToExp,[nnz,1,1,1,1]),[1,nzeta,neta,ntheta,nr]) - rtmp
	ToExp2 = etmp*tet*tet
	ToExp3 = tf.where(tf.greater(ToExp2,30),-30.0*tf.ones_like(ToExp2),-1.0*ToExp2)
	fac2 = tf.exp(ToExp3)
	# And finally the last two factors
	fac3 = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros_like(RijRij, dtype=prec),0.5*(tf.cos(3.14159265359*RijRij/R_cut)+1.0))
	fac4 = tf.where(tf.greater_equal(RikRik,R_cut),tf.zeros_like(RikRik, dtype=prec),0.5*(tf.cos(3.14159265359*RikRik/R_cut)+1.0))
	# assemble the full symmetry function for all triples.
	fac34t =  tf.tile(tf.reshape(fac3*fac4,[nnz,1,1,1,1]),[1,nzeta,neta,ntheta,nr])
	Gm = tf.reshape(fac1*fac2*fac34t,[nnz*nzeta*neta*ntheta*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	jk2 = tf.add(tf.multiply(tf.slice(GoodInds,[0,2],[nnz,1]), natom), tf.slice(GoodInds,[0,3],[nnz, 1]))
	mil_jk2 = tf.concat([tf.slice(GoodInds,[0,0],[nnz,2]),tf.slice(GoodInds,[0,4],[nnz,1]),tf.reshape(jk2,[nnz,1])],axis=-1)
	mil_jk_Outer2 = tf.tile(tf.reshape(mil_jk2,[nnz,1,4]),[1,nsym,1])
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.range(nzeta), neta*ntheta*nr),[nzeta,1]),[1,neta])
	p2_2 = tf.tile(tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.multiply(tf.range(neta),ntheta*nr),[1,neta]),[nzeta,1])],axis=-1),[nzeta,neta,1,2]),[1,1,ntheta,1])
	p3_2 = tf.tile(tf.reshape(tf.concat([p2_2,tf.tile(tf.reshape(tf.multiply(tf.range(ntheta),nr),[1,1,ntheta,1]),[nzeta,neta,1,1])],axis=-1),[nzeta,neta,ntheta,1,3]),[1,1,1,nr,1])
	p4_2 = tf.reshape(tf.concat([p3_2,tf.tile(tf.reshape(tf.range(nr),[1,1,1,nr,1]),[nzeta,neta,ntheta,1,1])],axis=-1),[1,nzeta,neta,ntheta,nr,4])
	p5_2 = tf.reshape(tf.reduce_sum(p4_2,axis=-1),[1,nsym,1]) # scatter_nd only supports upto rank 5... so gotta smush this...
	p6_2 = tf.tile(p5_2,[nnz,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_jk_Outer2,p6_2],axis=-1),[nnz*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,[nmol,natom,nelep,natom2,nsym])
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)


def TFSymASet_Update(R, Zs, eleps_, SFPs_, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eleps_: a nelepairs X 2 tensor of element pairs present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 4 X nzeta X neta X thetas X nRs. For example, SFPs_[0,0,0,0,0]
	    is the first zeta parameter. SFPs_[3,0,0,0,1] is the second R parameter.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	natom3 = natom*natom2
	nelep = tf.shape(eleps_)[0]
	pshape = tf.shape(SFPs_)
	nzeta = pshape[1]
	neta = pshape[2]
	ntheta = pshape[3]
	nr = pshape[4]
	nsym = nzeta*neta*ntheta*nr
	infinitesimal = 0.000000000000000000000000001
	onescalar = 1.0 - 0.0000000000000001

	# atom triples.
	ats = AllTriplesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0,0],[nmol,natom,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,0,1],[nmol,natom,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,0,2],[nmol,natom,natom,natom,1])
	Rk_inds = tf.slice(ats,[0,0,0,0,3],[nmol,natom,natom,natom,1])
	Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	Z1Z2 = ZouterSet(Zs)
	ZPairs = tf.gather_nd(Z1Z2,Rjk_inds) # should have shape nmol X natom3 X 2
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom3,1,2]),tf.reshape(eleps_,[1,1,nelep,2])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.logical_and(tf.not_equal(Ri_inds,Rj_inds),tf.not_equal(Ri_inds,Rk_inds)),[nmol,natom3,1]),[1,1,nelep])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.range(nelep)
	ats = tf.tile(tf.reshape(ats,[nmol,natom3,1,4]),[1,1,nelep,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nelep,1]),[nmol,natom3,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom3 * nelep X 5 (mol, i,j,k,l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	miks = tf.concat([tf.slice(GoodInds,[0,0],[nnz,2]),tf.slice(GoodInds,[0,3],[nnz,1])],axis=-1)
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	B = tf.gather_nd(Rij,miks)
	RijRik = tf.reduce_sum(A*B,axis=1)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)
	RikRik = tf.sqrt(tf.reduce_sum(B*B,axis=1)+infinitesimal)

	MaskDist1 = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	MaskDist2 = tf.where(tf.greater_equal(RikRik,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	MaskDist12 = tf.logical_and(MaskDist1, MaskDist2) # nmol X natom3 X nelep
	GoodInds2 = tf.boolean_mask(GoodInds, MaskDist12)
	nnz2 = tf.shape(GoodInds2)[0]
	mijs2 = tf.slice(GoodInds2,[0,0],[nnz2,3])
	miks2 = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,3],[nnz2,1])],axis=-1)
	A2 = tf.gather_nd(Rij,mijs2)
	B2 = tf.gather_nd(Rij,miks2)
	RijRik2 = tf.reduce_sum(A2*B2,axis=1)
	RijRij2 = tf.sqrt(tf.reduce_sum(A2*A2,axis=1)+infinitesimal)
	RikRik2 = tf.sqrt(tf.reduce_sum(B2*B2,axis=1)+infinitesimal)

	denom = RijRij2*RikRik2
	# Mask any troublesome entries.
	ToACos = RijRik2/denom
	ToACos = tf.where(tf.greater_equal(ToACos,1.0),tf.ones_like(ToACos, dtype=prec)*onescalar,ToACos)
	ToACos = tf.where(tf.less_equal(ToACos,-1.0),-1.0*tf.ones_like(ToACos, dtype=prec)*onescalar,ToACos)
	Thetaijk = tf.acos(ToACos)
	zetatmp = tf.cast(tf.reshape(SFPs_[0],[1,nzeta,neta,ntheta,nr]),prec)
	thetatmp = tf.cast(tf.tile(tf.reshape(SFPs_[2],[1,nzeta,neta,ntheta,nr]),[nnz2,1,1,1,1]),prec)
	# Broadcast the thetas and ToCos together
	tct = tf.tile(tf.reshape(Thetaijk,[nnz2,1,1,1,1]),[1,nzeta,neta,ntheta,nr], name="tct")
	ToCos = tct-thetatmp
	Tijk = tf.cos(ToCos) # shape: natom3 X ...
	# complete factor 1
	fac1 = tf.pow(tf.cast(2.0, prec),1.0-zetatmp)*tf.pow((1.0+Tijk),zetatmp)
	etmp = tf.cast(tf.reshape(SFPs_[1],[1,nzeta,neta,ntheta,nr]),prec) # ijk X zeta X eta ....
	rtmp = tf.cast(tf.reshape(SFPs_[3],[1,nzeta,neta,ntheta,nr]),prec) # ijk X zeta X eta ....
	ToExp = ((RijRij2+RikRik2)/2.0)
	tet = tf.tile(tf.reshape(ToExp,[nnz2,1,1,1,1]),[1,nzeta,neta,ntheta,nr], name="tet") - rtmp
	fac2 = tf.exp(-etmp*tet*tet)
	# And finally the last two factors
	fac3 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac4 = 0.5*(tf.cos(3.14159265359*RikRik2/R_cut)+1.0)
	# assemble the full symmetry function for all triples.
	fac34t =  tf.tile(tf.reshape(fac3*fac4,[nnz2,1,1,1,1]),[1,nzeta,neta,ntheta,nr], name="fac34t")
	Gm = tf.reshape(fac1*fac2*fac34t,[nnz2*nzeta*neta*ntheta*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	jk2 = tf.add(tf.multiply(tf.slice(GoodInds2,[0,2],[nnz2,1]), natom), tf.slice(GoodInds2,[0,3],[nnz2, 1]))
	mil_jk2 = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,4],[nnz2,1]),tf.reshape(jk2,[nnz2,1])],axis=-1)
	mil_jk_Outer2 = tf.tile(tf.reshape(mil_jk2,[nnz2,1,4]),[1,nsym,1], name="mil_jk_Outer2")
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.range(nzeta), neta*ntheta*nr),[nzeta,1]),[1,neta])
	p2_2 = tf.tile(tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.multiply(tf.range(neta),ntheta*nr),[1,neta]),[nzeta,1])],axis=-1),[nzeta,neta,1,2]),[1,1,ntheta,1])
	p3_2 = tf.tile(tf.reshape(tf.concat([p2_2,tf.tile(tf.reshape(tf.multiply(tf.range(ntheta),nr),[1,1,ntheta,1]),[nzeta,neta,1,1])],axis=-1),[nzeta,neta,ntheta,1,3]),[1,1,1,nr,1])
	p4_2 = tf.reshape(tf.concat([p3_2,tf.tile(tf.reshape(tf.range(nr),[1,1,1,nr,1]),[nzeta,neta,ntheta,1,1])],axis=-1),[1,nzeta,neta,ntheta,nr,4])
	p5_2 = tf.reshape(tf.reduce_sum(p4_2,axis=-1),[1,nsym,1]) # scatter_nd only supports upto rank 5... so gotta smush this...
	p6_2 = tf.tile(p5_2,[nnz2,1,1], name="p6_tile") # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_jk_Outer2,p6_2],axis=-1),[nnz2*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,[nmol,natom,nelep,natom2,nsym])
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)


def TFSymRSet(R, Zs, eles_, SFPs_, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eles_: a nelepairs X 1 tensor of elements present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 2 X neta  X nRs.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	nele = tf.shape(eles_)[0]
	pshape = tf.shape(SFPs_)
	neta = pshape[1]
	nr = pshape[2]
	nsym = neta*nr
	infinitesimal = 0.000000000000000000000000001

	# atom triples.
	ats = AllDoublesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0],[nmol,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,1],[nmol,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,2],[nmol,natom,natom,1])
	#Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	ZAll = AllDoublesSet(Zs)
	ZPairs = tf.slice(ZAll,[0,0,0,2],[nmol,natom,natom,1]) # should have shape nmol X natom X natom X 1
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom2,1,1]),tf.reshape(eles_,[1,1,nele,1])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.not_equal(Ri_inds,Rj_inds),[nmol,natom2,1]),[1,1,nele])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.range(nele)
	ats = tf.tile(tf.reshape(ats,[nmol,natom2,1,3]),[1,1,nele,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nele,1]),[nmol,natom2,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom2 * nele X 4 (mol, i, j, l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)
	# Mask any troublesome entries.
	etmp = tf.cast(tf.reshape(SFPs_[0],[1,neta,nr]),prec) # ijk X zeta X eta ....
	rtmp = tf.cast(tf.reshape(SFPs_[1],[1,neta,nr]),prec) # ijk X zeta X eta ....
	tet = tf.tile(tf.reshape(RijRij,[nnz,1,1]),[1,neta,nr]) - rtmp
	fac1 = tf.exp(-etmp*tet*tet)
	# And finally the last two factors
	fac2 = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros_like(RijRij, dtype=prec),0.5*(tf.cos(3.14159265359*RijRij/R_cut)+1.0))
	fac2t = tf.tile(tf.reshape(fac2,[nnz,1,1]),[1,neta,nr])
	# assemble the full symmetry function for all triples.
	Gm = tf.reshape(fac1*fac2t,[nnz*neta*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	mil_j = tf.concat([tf.slice(GoodInds,[0,0],[nnz,2]),tf.slice(GoodInds,[0,3],[nnz,1]),tf.slice(GoodInds,[0,2],[nnz,1])],axis=-1)
	mil_j_Outer = tf.tile(tf.reshape(mil_j,[nnz,1,4]),[1,nsym,1])
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.range(neta), nr),[neta,1,1]),[1,nr,1])
	p2_2 = tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.range(nr),[1,nr,1]),[neta,1,1])],axis=-1),[1,neta,nr,2])
	p3_2 = tf.reshape(tf.reduce_sum(p2_2,axis=-1),[1,nsym,1]) # scatter_nd only supports up to rank 5... so gotta smush this...
	p4_2 = tf.tile(p3_2,[nnz,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_j_Outer,p4_2],axis=-1),[nnz*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,[nmol,natom,nele,natom,nsym])
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)


def TFSymRSet_Update(R, Zs, eles_, SFPs_, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eles_: a nelepairs X 1 tensor of elements present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 2 X neta  X nRs.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	nele = tf.shape(eles_)[0]
	pshape = tf.shape(SFPs_)
	neta = pshape[1]
	nr = pshape[2]
	nsym = neta*nr
	infinitesimal = 0.000000000000000000000000001

	# atom triples.
	ats = AllDoublesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0],[nmol,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,1],[nmol,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,2],[nmol,natom,natom,1])
	#Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	ZAll = AllDoublesSet(Zs)
	ZPairs = tf.slice(ZAll,[0,0,0,2],[nmol,natom,natom,1]) # should have shape nmol X natom X natom X 1
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom2,1,1]),tf.reshape(eles_,[1,1,nele,1])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.not_equal(Ri_inds,Rj_inds),[nmol,natom2,1]),[1,1,nele])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.range(nele)
	ats = tf.tile(tf.reshape(ats,[nmol,natom2,1,3]),[1,1,nele,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nele,1]),[nmol,natom2,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom2 * nele X 4 (mol, i, j, l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)

	MaskDist = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	GoodInds2 = tf.boolean_mask(GoodInds, MaskDist)
	nnz2 = tf.shape(GoodInds2)[0]
	mijs2 = tf.slice(GoodInds2,[0,0],[nnz2,3])
	A2 = tf.gather_nd(Rij,mijs2)
	RijRij2 = tf.sqrt(tf.reduce_sum(A2*A2,axis=1)+infinitesimal)

	# Mask any troublesome entries.
	etmp = tf.cast(tf.reshape(SFPs_[0],[1,neta,nr]),prec) # ijk X zeta X eta ....
	rtmp = tf.cast(tf.reshape(SFPs_[1],[1,neta,nr]),prec) # ijk X zeta X eta ....
	tet = tf.tile(tf.reshape(RijRij2,[nnz2,1,1]),[1,neta,nr]) - rtmp
	fac1 = tf.exp(-etmp*tet*tet)
	# And finally the last two factors
	fac2 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac2t = tf.tile(tf.reshape(fac2,[nnz2,1,1]),[1,neta,nr])
	# assemble the full symmetry function for all triples.
	Gm = tf.reshape(fac1*fac2t,[nnz2*neta*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	mil_j = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,3],[nnz2,1]),tf.slice(GoodInds2,[0,2],[nnz2,1])],axis=-1)
	mil_j_Outer = tf.tile(tf.reshape(mil_j,[nnz2,1,4]),[1,nsym,1])
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.range(neta), nr),[neta,1,1]),[1,nr,1])
	p2_2 = tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.range(nr),[1,nr,1]),[neta,1,1])],axis=-1),[1,neta,nr,2])
	p3_2 = tf.reshape(tf.reduce_sum(p2_2,axis=-1),[1,nsym,1]) # scatter_nd only supports up to rank 5... so gotta smush this...
	p4_2 = tf.tile(p3_2,[nnz2,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_j_Outer,p4_2],axis=-1),[nnz2*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,[nmol,natom,nele,natom,nsym])
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)


def TFSymASet_Update2(R, Zs, eleps_, SFPs_, zeta, eta, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eleps_: a nelepairs X 2 tensor of element pairs present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 4 X nzeta X neta X thetas X nRs. For example, SFPs_[0,0,0,0,0]
	    is the first zeta parameter. SFPs_[3,0,0,0,1] is the second R parameter.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
        natom = inp_shp[1]
	natom2 = natom*natom
	natom3 = natom*natom2
	nelep = tf.shape(eleps_)[0]
	pshape = tf.shape(SFPs_)
	ntheta = pshape[1]
	nr = pshape[2]
	nsym = ntheta*nr
	infinitesimal = 0.000000000000000000000000001
	onescalar = 1.0 - 0.0000000000000001

	# atom triples.
	ats = AllTriplesSet(tf.cast(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]), dtype=tf.int64), prec=tf.int64)
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0,0],[nmol,natom,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,0,1],[nmol,natom,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,0,2],[nmol,natom,natom,natom,1])
	Rk_inds = tf.slice(ats,[0,0,0,0,3],[nmol,natom,natom,natom,1])
	Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	Z1Z2 = ZouterSet(Zs)
	ZPairs = tf.gather_nd(Z1Z2,Rjk_inds) # should have shape nmol X natom3 X 2
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom3,1,2]),tf.reshape(eleps_,[1,1,nelep,2])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.logical_and(tf.not_equal(Ri_inds,Rj_inds),tf.not_equal(Ri_inds,Rk_inds)),[nmol,natom3,1]),[1,1,nelep])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.cast(tf.range(nelep),dtype=tf.int64)
	ats = tf.tile(tf.reshape(ats,[nmol,natom3,1,4]),[1,1,nelep,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nelep,1]),[nmol,natom3,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom3 * nelep X 5 (mol, i,j,k,l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	miks = tf.concat([tf.slice(GoodInds,[0,0],[nnz,2]),tf.slice(GoodInds,[0,3],[nnz,1])],axis=-1)
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	B = tf.gather_nd(Rij,miks)
	RijRik = tf.reduce_sum(A*B,axis=1)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)
	RikRik = tf.sqrt(tf.reduce_sum(B*B,axis=1)+infinitesimal)

	MaskDist1 = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	MaskDist2 = tf.where(tf.greater_equal(RikRik,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	MaskDist12 = tf.logical_and(MaskDist1, MaskDist2) # nmol X natom3 X nelep
	GoodInds2 = tf.boolean_mask(GoodInds, MaskDist12)
	nnz2 = tf.shape(GoodInds2)[0]
	mijs2 = tf.slice(GoodInds2,[0,0],[nnz2,3])
	miks2 = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,3],[nnz2,1])],axis=-1)
	A2 = tf.gather_nd(Rij,mijs2)
	B2 = tf.gather_nd(Rij,miks2)
	RijRik2 = tf.reduce_sum(A2*B2,axis=1)
	RijRij2 = tf.sqrt(tf.reduce_sum(A2*A2,axis=1)+infinitesimal)
	RikRik2 = tf.sqrt(tf.reduce_sum(B2*B2,axis=1)+infinitesimal)

	denom = RijRij2*RikRik2
	#Mask any troublesome entries.
	ToACos = RijRik2/denom
	ToACos = tf.where(tf.greater_equal(ToACos,1.0),tf.ones_like(ToACos, dtype=prec)*onescalar, ToACos)
	ToACos = tf.where(tf.less_equal(ToACos,-1.0),-1.0*tf.ones_like(ToACos, dtype=prec)*onescalar, ToACos)
	Thetaijk = tf.acos(ToACos)
	thetatmp = tf.cast(tf.tile(tf.reshape(SFPs_[0],[1,ntheta,nr]),[nnz2,1,1]),prec)
	# Broadcast the thetas and ToCos together
	tct = tf.tile(tf.reshape(Thetaijk,[nnz2,1,1]),[1,ntheta,nr])
	ToCos = tct-thetatmp
	Tijk = tf.cos(ToCos) # shape: natom3 X ...
	# complete factor 1
	fac1 = tf.pow(tf.cast(2.0, prec),1.0-zeta)*tf.pow((1.0+Tijk),zeta)
	rtmp = tf.cast(tf.reshape(SFPs_[1],[1,ntheta,nr]),prec) # ijk X zeta X eta ....
	ToExp = ((RijRij2+RikRik2)/2.0)
	tet = tf.tile(tf.reshape(ToExp,[nnz2,1,1]),[1,ntheta,nr]) - rtmp
	fac2 = tf.exp(-eta*tet*tet)
	# And finally the last two factors
	fac3 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac4 = 0.5*(tf.cos(3.14159265359*RikRik2/R_cut)+1.0)
	# assemble the full symmetry function for all triples.
	fac34t =  tf.tile(tf.reshape(fac3*fac4,[nnz2,1,1]),[1,ntheta,nr])
	#Gm = tf.reshape(fac2*fac34t,[nnz2*ntheta*nr]) # nnz X nzeta X neta X ntheta X nr
	Gm = tf.reshape(fac1*fac2*fac34t,[nnz2*ntheta*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	jk2 = tf.add(tf.multiply(tf.slice(GoodInds2,[0,2],[nnz2,1]), tf.cast(natom, dtype=tf.int64)), tf.slice(GoodInds2,[0,3],[nnz2, 1]))
	mil_jk2 = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,4],[nnz2,1]),tf.reshape(jk2,[nnz2,1])],axis=-1)
	mil_jk_Outer2 = tf.tile(tf.reshape(mil_jk2,[nnz2,1,4]),[1,nsym,1])
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.

	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.cast(tf.range(ntheta), dtype=tf.int64), tf.cast(nr, dtype=tf.int64)),[ntheta,1,1]),[1,nr,1])
	p2_2 = tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.cast(tf.range(nr), dtype=tf.int64),[1,nr,1]),[ntheta,1,1])],axis=-1),[1,ntheta,nr,2])
	p3_2 = tf.reshape(tf.reduce_sum(p2_2,axis=-1),[1,nsym,1]) # scatter_nd only supports up to rank 5... so gotta smush this...
	p6_2 = tf.tile(p3_2,[nnz2,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_jk_Outer2,p6_2],axis=-1),[nnz2*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,tf.cast([nmol,natom,nelep,natom2,nsym], dtype=tf.int64))
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)



def TFSymRSet_Update2(R, Zs, eles_, SFPs_, eta, R_cut, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eles_: a nelepairs X 1 tensor of elements present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 2 X neta  X nRs.
	    R_cut: Radial Cutoff
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
        natom = inp_shp[1]
	natom2 = natom*natom
	nele = tf.shape(eles_)[0]
	pshape = tf.shape(SFPs_)
	nr = pshape[1]
	nsym = nr
	infinitesimal = 0.000000000000000000000000001

	# atom triples.
	ats = AllDoublesSet(tf.cast(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]), dtype=tf.int64), prec=tf.int64)
	# before performing any computation reduce this to desired pairs.
	# Construct the angle triples acos(<Rij,Rik>/|Rij||Rik|) and mask them onto the correct output
	# Get Rij, Rik...
	Rm_inds = tf.slice(ats,[0,0,0,0],[nmol,natom,natom,1])
	Ri_inds = tf.slice(ats,[0,0,0,1],[nmol,natom,natom,1])
	Rj_inds = tf.slice(ats,[0,0,0,2],[nmol,natom,natom,1])
	#Rjk_inds = tf.reshape(tf.concat([Rm_inds,Rj_inds,Rk_inds],axis=4),[nmol,natom3,3])
	ZAll = AllDoublesSet(Zs, prec=tf.int64)
	ZPairs = tf.slice(ZAll,[0,0,0,2],[nmol,natom,natom,1]) # should have shape nmol X natom X natom X 1
	ElemReduceMask = tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nmol,natom2,1,1]),tf.reshape(eles_,[1,1,nele,1])),axis=-1) # nmol X natom3 X nelep
	# Zero out the diagonal contributions (i==j or i==k)
	IdentMask = tf.tile(tf.reshape(tf.not_equal(Ri_inds,Rj_inds),[nmol,natom2,1]),[1,1,nele])
	Mask = tf.logical_and(ElemReduceMask,IdentMask) # nmol X natom3 X nelep
	# Mask is true if atoms ijk => pair_l and many triples are unused.
	# So we create a final index tensor, which is only nonzero m,ijk,l
	pinds = tf.cast(tf.range(nele), dtype=tf.int64)
	ats = tf.tile(tf.reshape(ats,[nmol,natom2,1,3]),[1,1,nele,1])
	ps = tf.tile(tf.reshape(pinds,[1,1,nele,1]),[nmol,natom2,1,1])
	ToMask = tf.concat([ats,ps],axis=3)
	GoodInds = tf.boolean_mask(ToMask,Mask)
	nnz = tf.shape(GoodInds)[0]
	# Good Inds has shape << nmol * natom2 * nele X 4 (mol, i, j, l=element pair.)
	# and contains all the indices we actually want to compute, Now we just slice, gather and compute.
	mijs = tf.slice(GoodInds,[0,0],[nnz,3])
	Rij = DifferenceVectorsSet(R,prec) # nmol X atom X atom X 3
	A = tf.gather_nd(Rij,mijs)
	RijRij = tf.sqrt(tf.reduce_sum(A*A,axis=1)+infinitesimal)

	MaskDist = tf.where(tf.greater_equal(RijRij,R_cut),tf.zeros([nnz], dtype=tf.bool), tf.ones([nnz], dtype=tf.bool))
	GoodInds2 = tf.boolean_mask(GoodInds, MaskDist)
	nnz2 = tf.shape(GoodInds2)[0]
	mijs2 = tf.slice(GoodInds2,[0,0],[nnz2,3])
	A2 = tf.gather_nd(Rij,mijs2)
	RijRij2 = tf.sqrt(tf.reduce_sum(A2*A2,axis=1)+infinitesimal)

	# Mask any troublesome entries.
	rtmp = tf.cast(tf.reshape(SFPs_[0],[1,nr]),prec) # ijk X zeta X eta ....
	tet = tf.tile(tf.reshape(RijRij2,[nnz2,1]),[1,nr]) - rtmp
	fac1 = tf.exp(-eta*tet*tet)
	# And finally the last two factors
	fac2 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac2t = tf.tile(tf.reshape(fac2,[nnz2,1]),[1,nr])
	# assemble the full symmetry function for all triples.
	Gm = tf.reshape(fac1*fac2t,[nnz2*nr]) # nnz X nzeta X neta X ntheta X nr
	# Finally scatter out the symmetry functions where they belong.
	mil_j = tf.concat([tf.slice(GoodInds2,[0,0],[nnz2,2]),tf.slice(GoodInds2,[0,3],[nnz2,1]),tf.slice(GoodInds2,[0,2],[nnz2,1])],axis=-1)
	mil_j_Outer = tf.tile(tf.reshape(mil_j,[nnz2,1,4]),[1,nsym,1])
	# So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p2_2 = tf.reshape(tf.reshape(tf.cast(tf.range(nr), dtype=tf.int64),[nr,1]),[1,nr,1])
	p4_2 = tf.tile(p2_2,[nnz2,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_j_Outer,p4_2],axis=-1),[nnz2*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,tf.cast([nmol,natom,nele,natom,nsym], dtype=tf.int64))
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)


def TFSymASet_Linear(R, Zs, eleps_, SFPs_, zeta, eta, R_cut, Angtri, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom X 1 tensor of atomic numbers.
		eleps_: a nelepairs X 2 tensor of element pairs present in the data.
		SFP: A symmetry function parameter tensor having the number of elements
		as the SF output. 4 X nzeta X neta X thetas X nRs. For example, SFPs_[0,0,0,0,0]
		is the first zeta parameter. SFPs_[3,0,0,0,1] is the second R parameter.
		R_cut: Radial Cutoff
		Angtri: angular triples within the cutoff.
		prec: a precision.
	Returns:
		Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	natom3 = natom*natom2
	nelep = tf.shape(eleps_)[0]
	pshape = tf.shape(SFPs_)
	ntheta = pshape[1]
	nr = pshape[2]
	nsym = ntheta*nr
	infinitesimal = 0.000000000000000000000000001
	onescalar = 1.0 - 0.0000000000000001
	nnzt = tf.shape(Angtri)[0]

	Z1Z2 = ZouterSet(Zs)

	Rij_inds = tf.slice(Angtri,[0,0],[nnzt,3])
	Rik_inds = tf.concat([tf.slice(Angtri,[0,0],[nnzt,2]), tf.slice(Angtri,[0,3],[nnzt,1])],axis=-1)
	Rjk_inds = tf.concat([tf.slice(Angtri,[0,0],[nnzt,1]), tf.slice(Angtri,[0,2],[nnzt,2])],axis=-1)
	ZPairs = tf.gather_nd(Z1Z2, Rjk_inds)
	EleIndex = tf.slice(tf.where(tf.reduce_all(tf.equal(tf.reshape(ZPairs,[nnzt,1,2]), tf.reshape(eleps_,[1, nelep, 2])),axis=-1)),[0,1],[nnzt,1])
	GoodInds2 = tf.concat([Angtri,EleIndex],axis=-1)

	Rij = DifferenceVectorsLinear(R, Rij_inds)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=1)+infinitesimal)
	Rik = DifferenceVectorsLinear(R, Rik_inds)
	RikRik2 = tf.sqrt(tf.reduce_sum(Rik*Rik,axis=1)+infinitesimal)
	RijRik2 = tf.reduce_sum(Rij*Rik, axis=1)
	denom = RijRij2*RikRik2
	#Mask any troublesome entries.
	ToACos = RijRik2/denom
	ToACos = tf.where(tf.greater_equal(ToACos,1.0),tf.ones_like(ToACos, dtype=prec)*onescalar, ToACos)
	ToACos = tf.where(tf.less_equal(ToACos,-1.0),-1.0*tf.ones_like(ToACos, dtype=prec)*onescalar, ToACos)
	Thetaijk = tf.acos(ToACos)
	thetatmp = tf.cast(tf.tile(tf.reshape(SFPs_[0],[1,ntheta,nr]),[nnzt,1,1]),prec)
	# Broadcast the thetas and ToCos together
	tct = tf.tile(tf.reshape(Thetaijk,[nnzt,1,1]),[1,ntheta,nr])
	ToCos = tct-thetatmp
	Tijk = tf.cos(ToCos) # shape: natom3 X ...
	# complete factor 1
	fac1 = tf.pow(tf.cast(2.0, prec),1.0-zeta)*tf.pow((1.0+Tijk),zeta)
	rtmp = tf.cast(tf.reshape(SFPs_[1],[1,ntheta,nr]),prec) # ijk X zeta X eta ....
	ToExp = ((RijRij2+RikRik2)/2.0)
	tet = tf.tile(tf.reshape(ToExp,[nnzt,1,1]),[1,ntheta,nr]) - rtmp
	fac2 = tf.exp(-eta*tet*tet)
	# And finally the last two factors
	fac3 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac4 = 0.5*(tf.cos(3.14159265359*RikRik2/R_cut)+1.0)
	## assemble the full symmetry function for all triples.
	fac34t =  tf.tile(tf.reshape(fac3*fac4,[nnzt,1,1]),[1,ntheta,nr])
	Gm = tf.reshape(fac1*fac2*fac34t,[nnzt*ntheta*nr]) # nnz X nzeta X neta X ntheta X nr
	## Finally scatter out the symmetry functions where they belong.
	jk2 = tf.add(tf.multiply(tf.slice(GoodInds2,[0,2],[nnzt,1]), tf.cast(natom, dtype=tf.int64)), tf.slice(GoodInds2,[0,3],[nnzt, 1]))
	mil_jk2 = tf.concat([tf.slice(GoodInds2,[0,0],[nnzt,2]),tf.slice(GoodInds2,[0,4],[nnzt,1]),tf.reshape(jk2,[nnzt,1])],axis=-1)
	mil_jk_Outer2 = tf.tile(tf.reshape(mil_jk2,[nnzt,1,4]),[1,nsym,1])
	## So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p1_2 = tf.tile(tf.reshape(tf.multiply(tf.cast(tf.range(ntheta), dtype=tf.int64), tf.cast(nr, dtype=tf.int64)),[ntheta,1,1]),[1,nr,1])
	p2_2 = tf.reshape(tf.concat([p1_2,tf.tile(tf.reshape(tf.cast(tf.range(nr), dtype=tf.int64),[1,nr,1]),[ntheta,1,1])],axis=-1),[1,ntheta,nr,2])
	p3_2 = tf.reshape(tf.reduce_sum(p2_2,axis=-1),[1,nsym,1]) # scatter_nd only supports up to rank 5... so gotta smush this...
	p6_2 = tf.tile(p3_2,[nnzt,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_jk_Outer2,p6_2],axis=-1),[nnzt*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,tf.cast([nmol,natom,nelep,natom2,nsym], dtype=tf.int64))
	return tf.reduce_sum(to_reduce2, axis=3)

def TFCoulomb(R, Qs, R_cut, Radpair, prec=tf.float64):
	"""
	Tensorflow implementation of sparse-coulomb
	Madelung energy build.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Qs : nmol X maxnatom X 1 tensor of atomic charges.
	    R_cut: Radial Cutoff
	    Radpair: None zero pairs X 3 tensor (mol, i, j)
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	infinitesimal = 0.000000000000000000000000001
	nnz = tf.shape(Radpair)[0]
	Rij = DifferenceVectorsLinear(R, Radpair)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=-1)+infinitesimal)
	# Grab the Q's.
	Qii = tf.slice(Radpair,[0,0],[-1,2])
	Qji = tf.concat([tf.slice(Radpair,[0,0],[-1,1]),tf.slice(Radpair,[0,2],[-1,1])], axis=-1)
	Qi = tf.gather_nd(Qs,Qii)
	Qj = tf.gather_nd(Qs,Qji)
	# Finish the Kernel.
	Kern = Qi*Qj/RijRij2
	mol_index = tf.cast(tf.reshape(tf.slice(Radpair,[0,0],[-1,1]),[nnz]), dtype=tf.int64)
	range_index = tf.range(tf.cast(nnz, tf.int64), dtype=tf.int64)
	sparse_index =tf.stack([mol_index, range_index], axis=1)
	sp_atomoutputs = tf.SparseTensor(sparse_index, Kern, dense_shape=[tf.cast(nmol, tf.int64), tf.cast(nnz, tf.int64)])
	E_ee = tf.sparse_reduce_sum(sp_atomoutputs, axis=1)
	return E_ee


def TFCoulombCosLR(R, Qs, R_cut, Radpair, prec=tf.float64):
	"""
	Tensorflow implementation of long range cutoff sparse-coulomb
	Madelung energy build.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Qs : nmol X maxnatom X 1 tensor of atomic charges.
	    R_cut: Radial Cutoff
	    Radpair: None zero pairs X 3 tensor (mol, i, j)
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	infinitesimal = 0.000000000000000000000000001
	nnz = tf.shape(Radpair)[0]
	Rij = DifferenceVectorsLinear(R, Radpair)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=1)+infinitesimal)
	# Generate LR cutoff Matrix
	Cut = (1.0-0.5*(tf.cos(RijRij2*Pi/R_cut)+1.0))
	# Grab the Q's.
	Qii = tf.slice(Radpair,[0,0],[-1,2])
	Qji = tf.concat([tf.slice(Radpair,[0,0],[-1,1]),tf.slice(Radpair,[0,2],[-1,1])], axis=-1)
	Qi = tf.gather_nd(Qs,Qii)
	Qj = tf.gather_nd(Qs,Qji)
	# Finish the Kernel.
	Kern = Qi*Qj/RijRij2*Cut
	# Scatter Back
	mol_index = tf.cast(tf.reshape(tf.slice(Radpair,[0,0],[-1,1]),[nnz]), dtype=tf.int64)
	range_index = tf.range(tf.cast(nnz, tf.int64), dtype=tf.int64)
	sparse_index =tf.stack([mol_index, range_index], axis=1)
	sp_atomoutputs = tf.SparseTensor(sparse_index, Kern, dense_shape=[tf.cast(nmol, tf.int64), tf.cast(nnz, tf.int64)])
	E_ee = tf.sparse_reduce_sum(sp_atomoutputs, axis=1)
	return E_ee


def TFCoulombErfLR(R, Qs, R_cut,  Radpair, prec=tf.float64):
	"""
	Tensorflow implementation of long range cutoff sparse-Erf
	Madelung energy build.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Qs : nmol X maxnatom X 1 tensor of atomic charges.
	    R_cut: Radial Cutoff
	    Radpair: None zero pairs X 3 tensor (mol, i, j)
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	R_width = PARAMS["Erf_Width"]*BOHRPERA
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	infinitesimal = 0.000000000000000000000000001
	nnz = tf.shape(Radpair)[0]
	Rij = DifferenceVectorsLinear(R, Radpair)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=1)+infinitesimal)
	# Generate LR cutoff Matrix
	Cut = (1.0 + tf.erf((RijRij2 - R_cut)/R_width))*0.5
	# Grab the Q's.
	Qii = tf.slice(Radpair,[0,0],[-1,2])
	Qji = tf.concat([tf.slice(Radpair,[0,0],[-1,1]),tf.slice(Radpair,[0,2],[-1,1])], axis=-1)
	Qi = tf.gather_nd(Qs,Qii)
	Qj = tf.gather_nd(Qs,Qji)
	# Finish the Kernel.
	Kern = Qi*Qj/RijRij2*Cut
	# Scatter Back
	mol_index = tf.cast(tf.reshape(tf.slice(Radpair,[0,0],[-1,1]),[nnz]), dtype=tf.int64)
	range_index = tf.range(tf.cast(nnz, tf.int64), dtype=tf.int64)
	sparse_index =tf.stack([mol_index, range_index], axis=1)
	sp_atomoutputs = tf.SparseTensor(sparse_index, Kern, dense_shape=[tf.cast(nmol, tf.int64), tf.cast(nnz, tf.int64)])
	E_ee = tf.sparse_reduce_sum(sp_atomoutputs, axis=1)
	return E_ee


def TFCoulombErfSRDSFLR(R, Qs, R_srcut, R_lrcut, Radpair, alpha, prec=tf.float64):
	"""
	A tensorflow linear scaling implementation of the Damped Shifted Electrostatic Force with short range cutoff
	http://aip.scitation.org.proxy.library.nd.edu/doi/pdf/10.1063/1.2206581
	Batched over molecules.

	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Qs : nmol X maxnatom X 1 tensor of atomic charges.
		R_srcut: Short Range Erf Cutoff
		R_lrcut: Long Range DSF Cutoff
		Radpair: None zero pairs X 3 tensor (mol, i, j)
		alpha: DSF alpha parameter (~0.2)
	Returns
		Energy of  Mols 
	"""
	R_width = PARAMS["Erf_Width"]*BOHRPERA
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	infinitesimal = 0.000000000000000000000000001
	nnz = tf.shape(Radpair)[0]
	Rij = DifferenceVectorsLinear(R, Radpair)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=1)+infinitesimal)
	Cut = (1.0 + tf.erf((RijRij2 - R_srcut)/R_width))*0.5

	twooversqrtpi = tf.constant(1.1283791671,dtype=tf.float64)
	Qii = tf.slice(Radpair,[0,0],[-1,2])
	Qji = tf.concat([tf.slice(Radpair,[0,0],[-1,1]),tf.slice(Radpair,[0,2],[-1,1])], axis=-1)
	Qi = tf.gather_nd(Qs,Qii)
	Qj = tf.gather_nd(Qs,Qji)
	# Gather desired LJ parameters.
	Qij = Qi*Qj
	# This is Dan's Equation (18)
	XX = alpha*R_lrcut
	ZZ = tf.erfc(XX)/R_lrcut
	YY = twooversqrtpi*alpha*tf.exp(-XX*XX)/R_lrcut
	K = Qij*(tf.erfc(alpha*RijRij2)/RijRij2 - ZZ + (RijRij2-R_lrcut)*(ZZ/R_lrcut+YY))*Cut
	K = tf.where(tf.is_nan(K),tf.zeros_like(K),K)
	range_index = tf.range(tf.cast(nnz, tf.int64), dtype=tf.int64)
	mol_index = tf.cast(tf.reshape(tf.slice(Radpair,[0,0],[-1,1]),[nnz]), dtype=tf.int64)
	sparse_index = tf.stack([mol_index, range_index], axis=1) 
	sp_atomoutputs = tf.SparseTensor(sparse_index, K, dense_shape=[tf.cast(nmol, tf.int64), tf.cast(nnz, tf.int64)])
	# Now use the sparse reduce sum trick to scatter this into mols.
	return tf.sparse_reduce_sum(sp_atomoutputs, axis=1)


def TFSymRSet_Linear(R, Zs, eles_, SFPs_, eta, R_cut, Radpair, prec=tf.float64):
	"""
	A tensorflow implementation of the angular AN1 symmetry function for a single input molecule.
	Here j,k are all other atoms, but implicitly the output
	is separated across elements as well. eleps_ is a list of element pairs
	G = 2**(1-zeta) \sum_{j,k \neq i} (Angular triple) (radial triple) f_c(R_{ij}) f_c(R_{ik})
	a-la MolEmb.cpp. Also depends on PARAMS for zeta, eta, theta_s r_s
	This version improves on the previous by avoiding some
	heavy tiles.

	Args:
	    R: a nmol X maxnatom X 3 tensor of coordinates.
	    Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	    eles_: a nelepairs X 1 tensor of elements present in the data.
	    SFP: A symmetry function parameter tensor having the number of elements
	    as the SF output. 2 X neta  X nRs.
	    R_cut: Radial Cutoff
	    Radpair: None zero pairs X 3 tensor (mol, i, j)
	    prec: a precision.
	Returns:
	    Digested Mol. In the shape nmol X maxnatom X nelepairs X nZeta X nEta X nThetas X nRs
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	natom2 = natom*natom
	nele = tf.shape(eles_)[0]
	pshape = tf.shape(SFPs_)
	nr = pshape[1]
	nsym = nr
	infinitesimal = 0.000000000000000000000000001
	nnz = tf.shape(Radpair)[0]
	#Rtmp = tf.concat([tf.slice(Radpair,[0,0],[nnz,1]), tf.slice(Radpair,[0,2],[nnz,1])], axis=-1)
	#Rreverse = tf.concat([Rtmp, tf.slice(Radpair,[0,1],[nnz,1])], axis=-1)
	#Rboth = tf.concat([Radpair, Rreverse], axis=0)
	Rij = DifferenceVectorsLinear(R, Radpair)
	RijRij2 = tf.sqrt(tf.reduce_sum(Rij*Rij,axis=1)+infinitesimal)
	ZAll = AllDoublesSet(Zs, prec=tf.int64)
	ZPairs = tf.slice(ZAll,[0,0,0,2],[nmol,natom,natom,1])
	Rl=tf.gather_nd(ZPairs, Radpair)
	ElemIndex = tf.slice(tf.where(tf.equal(Rl, tf.reshape(eles_,[1,nele]))),[0,1],[nnz,1])
	GoodInds2 = tf.concat([Radpair, ElemIndex], axis=-1)

	rtmp = tf.cast(tf.reshape(SFPs_[0],[1,nr]),prec) # ijk X zeta X eta ....
	tet = tf.tile(tf.reshape(RijRij2,[nnz,1]),[1,nr]) - rtmp
	fac1 = tf.exp(-eta*tet*tet)
	# And finally the last two factors
	fac2 = 0.5*(tf.cos(3.14159265359*RijRij2/R_cut)+1.0)
	fac2t = tf.tile(tf.reshape(fac2,[nnz,1]),[1,nr])
	## assemble the full symmetry function for all triples.
	Gm = tf.reshape(fac1*fac2t,[nnz*nr]) # nnz X nzeta X neta X ntheta X nr
	## Finally scatter out the symmetry functions where they belong.
	mil_j = tf.concat([tf.slice(GoodInds2,[0,0],[nnz,2]),tf.slice(GoodInds2,[0,3],[nnz,1]),tf.slice(GoodInds2,[0,2],[nnz,1])],axis=-1)
	mil_j_Outer = tf.tile(tf.reshape(mil_j,[nnz,1,4]),[1,nsym,1])
	## So the above is Mol, i, l... now must outer nzeta,neta,ntheta,nr to finish the indices.
	p2_2 = tf.reshape(tf.reshape(tf.cast(tf.range(nr), dtype=tf.int64),[nr,1]),[1,nr,1])
	p4_2 = tf.tile(p2_2,[nnz,1,1]) # should be nnz X nsym
	ind2 = tf.reshape(tf.concat([mil_j_Outer,p4_2],axis=-1),[nnz*nsym,5]) # This is now nnz*nzeta*neta*ntheta*nr X 8 -  m,i,l,jk,zeta,eta,theta,r
	to_reduce2 = tf.scatter_nd(ind2,Gm,tf.cast([nmol,natom,nele,natom,nsym], dtype=tf.int64))
	#to_reduce2 = tf.sparse_to_dense(ind2, tf.convert_to_tensor([nmol, natom, nelep, natom2, nsym]), Gm)
	#to_reduce_sparse = tf.SparseTensor(ind2,[nmol, natom, nelep, natom2, nzeta, neta, ntheta, nr])
	return tf.reduce_sum(to_reduce2, axis=3)

def TFSymSet(R, Zs, eles_, SFPsR_, Rr_cut, eleps_, SFPsA_, Ra_cut):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom X 1 tensor of atomic numbers.
		eles_: a neles X 1 tensor of elements present in the data.
		SFPsR_: A symmetry function parameter of radius part
		Rr_cut: Radial Cutoff of radius part
		eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
		SFPsA_: A symmetry function parameter of angular part
		RA_cut: Radial Cutoff of angular part

	Returns:
		Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nele = tf.shape(eles_)[0]
	nelep = tf.shape(eleps_)[0]
	GMR = tf.reshape(TFSymRSet(R, Zs, eles_, SFPsR_, Rr_cut),[nmol, natom, -1])
	GMA = tf.reshape(TFSymASet(R, Zs, eleps_, SFPsA_, Ra_cut),[nmol, natom, -1])
	GM = tf.concat([GMR, GMA], axis=2)
	return GM

def TFSymSet_Scattered(R, Zs, eles_, SFPsR_, Rr_cut, eleps_, SFPsA_, Ra_cut):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom X 1 tensor of atomic numbers.
		eles_: a neles X 1 tensor of elements present in the data.
		SFPsR_: A symmetry function parameter of radius part
		Rr_cut: Radial Cutoff of radius part
		eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
		SFPsA_: A symmetry function parameter of angular part
		RA_cut: Radial Cutoff of angular part

	Returns:
		Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nele = tf.shape(eles_)[0]
	nelep = tf.shape(eleps_)[0]
	GMR = tf.reshape(TFSymRSet(R, Zs, eles_, SFPsR_, Rr_cut),[nmol, natom, -1])
	GMA = tf.reshape(TFSymASet(R, Zs, eleps_, SFPsA_, Ra_cut),[nmol, natom, -1])
	GM = tf.concat([GMR, GMA], axis=2)
	num_ele, num_dim = eles_.get_shape().as_list()
	MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
	ToMask = AllSinglesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	IndexList = []
	SymList=[]
	GatherList = []
	for e in range(num_ele):
		GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
		SymList.append(tf.gather_nd(GM, GatherList[-1]))
		NAtomOfEle=tf.shape(GatherList[-1])[0]
		IndexList.append(tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle]))
	return SymList, IndexList

def TFSymSet_Scattered_Update(R, Zs, eles_, SFPsR_, Rr_cut,  eleps_, SFPsA_, Ra_cut):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom X 1 tensor of atomic numbers.
		eles_: a neles X 1 tensor of elements present in the data.
		SFPsR_: A symmetry function parameter of radius part
		Rr_cut: Radial Cutoff of radius part
		eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
		SFPsA_: A symmetry function parameter of angular part
		RA_cut: Radial Cutoff of angular part

	Returns:
		Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nele = tf.shape(eles_)[0]
	nelep = tf.shape(eleps_)[0]
	GMR = tf.reshape(TFSymRSet_Update(R, Zs, eles_, SFPsR_, Rr_cut), [nmol, natom, -1])
	GMA = tf.reshape(TFSymASet_Update(R, Zs, eleps_, SFPsA_, Ra_cut), [nmol, natom, -1])
	GM = tf.concat([GMR, GMA], axis=2)
	num_ele, num_dim = eles_.get_shape().as_list()
	MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
	ToMask = AllSinglesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	IndexList = []
	SymList=[]
	GatherList = []
	for e in range(num_ele):
		GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
		SymList.append(tf.gather_nd(GM, GatherList[-1]))
		NAtomOfEle=tf.shape(GatherList[-1])[0]
		IndexList.append(tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle]))
	return SymList, IndexList


def TFSymSet_Scattered_Update2(R, Zs, eles_, SFPsR_, Rr_cut,  eleps_, SFPsA_, zeta, eta, Ra_cut):
        """
        A tensorflow implementation of the AN1 symmetry function for a set of molecule.
        Args:
                R: a nmol X maxnatom X 3 tensor of coordinates.
                Zs : nmol X maxnatom X 1 tensor of atomic numbers.
                eles_: a neles X 1 tensor of elements present in the data.
                SFPsR_: A symmetry function parameter of radius part
                Rr_cut: Radial Cutoff of radius part
                eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
                SFPsA_: A symmetry function parameter of angular part
                RA_cut: Radial Cutoff of angular part

        Returns:
                Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
        """
        inp_shp = tf.shape(R)
	nmol = inp_shp[0]
        natom = inp_shp[1]
        nele = tf.shape(eles_)[0]
        nelep = tf.shape(eleps_)[0]
        GMR = tf.reshape(TFSymRSet_Update2(R, Zs, eles_, SFPsR_, eta, Rr_cut), [nmol, natom, -1])
        GMA = tf.reshape(TFSymASet_Update2(R, Zs, eleps_, SFPsA_, zeta,  eta, Ra_cut), [nmol, natom, -1])
        GM = tf.concat([GMR, GMA], axis=2)
        num_ele, num_dim = eles_.get_shape().as_list()
        MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
        ToMask = AllSinglesSet(tf.cast(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]),dtype=tf.int64), prec=tf.int64)
        IndexList = []
        SymList=[]
        GatherList = []
        for e in range(num_ele):
                GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
                SymList.append(tf.gather_nd(GM, GatherList[-1]))
                NAtomOfEle=tf.shape(GatherList[-1])[0]
                IndexList.append(tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle]))
        return SymList, IndexList

def TFSymSet_Scattered_Update_Scatter(R, Zs, eles_, SFPsR_, Rr_cut,  eleps_, SFPsA_, zeta, eta, Ra_cut):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
	        R: a nmol X maxnatom X 3 tensor of coordinates.
	        Zs : nmol X maxnatom X 1 tensor of atomic numbers.
	        eles_: a neles X 1 tensor of elements present in the data.
	        SFPsR_: A symmetry function parameter of radius part
	        Rr_cut: Radial Cutoff of radius part
	        eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
	        SFPsA_: A symmetry function parameter of angular part
	        RA_cut: Radial Cutoff of angular part

	Returns:
	        Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nele = tf.shape(eles_)[0]
	nelep = tf.shape(eleps_)[0]
	GMR = tf.reshape(TFSymRSet_Update2(R, Zs, eles_, SFPsR_, eta, Rr_cut), [nmol, natom, -1])
	GMA = tf.reshape(TFSymASet_Update2(R, Zs, eleps_, SFPsA_, zeta,  eta, Ra_cut), [nmol, natom, -1])
	GM = tf.concat([GMR, GMA], axis=2)
	num_ele, num_dim = eles_.get_shape().as_list()
	MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
	ToMask1 = AllSinglesSet(tf.cast(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]),dtype=tf.int64), prec=tf.int64)
	v = tf.cast(tf.reshape(tf.range(nmol*natom), [nmol, natom, 1]), dtype=tf.int64)
	ToMask = tf.concat([ToMask1, v], axis = -1)
	IndexList = []
	SymList= []
	GatherList = []
	for e in range(num_ele):
		GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
		NAtomOfEle=tf.shape(GatherList[-1])[0]
		SymList.append(tf.gather_nd(GM, tf.slice(GatherList[-1],[0,0],[NAtomOfEle,2])))
		mol_index = tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle, 1])
		atom_index = tf.reshape(tf.slice(GatherList[-1],[0,2],[NAtomOfEle,1]),[NAtomOfEle, 1])
		IndexList.append(tf.concat([mol_index, atom_index], axis = -1))
	return SymList, IndexList

def TFSymSet_Scattered_Linear(R, Zs, eles_, SFPsR_, Rr_cut,  eleps_, SFPsA_, zeta, eta, Ra_cut, Radp, Angt):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom X 1 tensor of atomic numbers.
		eles_: a neles X 1 tensor of elements present in the data.
		SFPsR_: A symmetry function parameter of radius part
		Rr_cut: Radial Cutoff of radius part
		eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
		SFPsA_: A symmetry function parameter of angular part
		RA_cut: Radial Cutoff of angular part
	Returns:
		Digested Mol. In the shape nmol X maxnatom X (Dimension of radius part + Dimension of angular part)
	"""
	inp_shp = tf.shape(R)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nele = tf.shape(eles_)[0]
	nelep = tf.shape(eleps_)[0]
	GMR = tf.reshape(TFSymRSet_Linear(R, Zs, eles_, SFPsR_, eta, Rr_cut, Radp),[nmol, natom,-1])
	GMA = tf.reshape(TFSymASet_Linear(R, Zs, eleps_, SFPsA_, zeta,  eta, Ra_cut,  Angt), [nmol, natom,-1])
	GM = tf.concat([GMR, GMA], axis=2)
	#GM = tf.identity(GMA)
	num_ele, num_dim = eles_.get_shape().as_list()
	MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
	ToMask1 = AllSinglesSet(tf.cast(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]),dtype=tf.int64), prec=tf.int64)
	v = tf.cast(tf.reshape(tf.range(nmol*natom), [nmol, natom, 1]), dtype=tf.int64)
	ToMask = tf.concat([ToMask1, v], axis = -1)
	IndexList = []
	SymList= []
	GatherList = []
	for e in range(num_ele):
		GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
		NAtomOfEle=tf.shape(GatherList[-1])[0]
		SymList.append(tf.gather_nd(GM, tf.slice(GatherList[-1],[0,0],[NAtomOfEle,2])))
		mol_index = tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle, 1])
		atom_index = tf.reshape(tf.slice(GatherList[-1],[0,2],[NAtomOfEle,1]),[NAtomOfEle, 1])
		IndexList.append(tf.concat([mol_index, atom_index], axis = -1))
	return SymList, IndexList


def NNInterface(R, Zs, eles_, GM):
	"""
	A tensorflow implementation of the AN1 symmetry function for a set of molecule.
	Args:
		R: a nmol X maxnatom X 3 tensor of coordinates.
		Zs : nmol X maxnatom  tensor of atomic numbers.
		eles_: a neles X 1 tensor of elements present in the data.
		eleps_: a nelepairs X 2 X 12tensor of elements pairs present in the data.
		GM: Unscattered ANI1 sym Func: nmol X natom X nele X Dim


	Returns:
		List of ANI SymFunc of each atom by element type.
		List of Mol index of each atom by element type.
	"""
	nele = tf.shape(eles_)[0]
	num_ele, num_dim = eles_.get_shape().as_list()
	R_shp = tf.shape(R)
	nmol = R_shp[0]
	natom = R_shp[1]
	MaskAll = tf.equal(tf.reshape(Zs,[nmol,natom,1]),tf.reshape(eles_,[1,1,nele]))
	ToMask = AllSinglesSet(tf.tile(tf.reshape(tf.range(natom),[1,natom]),[nmol,1]))
	IndexList = []
	SymList=[]
	GatherList = []
	for e in range(num_ele):
		GatherList.append(tf.boolean_mask(ToMask,tf.reshape(tf.slice(MaskAll,[0,0,e],[nmol,natom,1]),[nmol, natom])))
		SymList.append(tf.gather_nd(GM, GatherList[-1]))
		NAtomOfEle=tf.shape(GatherList[-1])[0]
		IndexList.append(tf.reshape(tf.slice(GatherList[-1],[0,0],[NAtomOfEle,1]),[NAtomOfEle]))
	return SymList, IndexList

def TFBond(Zxyzs, BndIdxMat, ElemPairs_):
	"""
	Tensorflow embedding of bond descriptor
	Args:
		Zxyzs: a nmol X maxnatom X 4 tensor of atomic Zs and coordinates.
		BndIdxMat: nbond X 3 matrix of (molecule, atom1, atom2) indices.
		ElemPairs_: a NumElementPairs X 2 of elements pairs present in the data.
	"""
	inp_shp = tf.shape(Zxyzs)
	nmol = inp_shp[0]
	natom = inp_shp[1]
	nelemp = tf.shape(ElemPairs_)[0]
	RMatrix = TFDistancesLinear(Zxyzs[:,:,1:], BndIdxMat)
	ZPairs = tf.cast(tf.stack([tf.gather_nd(Zxyzs[:,:,0], BndIdxMat[:,:2]),tf.gather_nd(Zxyzs[:,:,0], BndIdxMat[:,::2])],axis=1),dtype=tf.int32)
	# tf.nn.top_k is slow, next lines faster for sorting nx2 array of atomic Zs
	TmpZ1 = tf.gather_nd(ZPairs, tf.stack([tf.range(tf.shape(ZPairs)[0]),tf.cast(tf.argmin(ZPairs, axis=1), tf.int32)],axis=1))
	TmpZ2 = tf.gather_nd(ZPairs, tf.stack([tf.range(tf.shape(ZPairs)[0]),tf.cast(tf.argmax(ZPairs, axis=1), tf.int32)],axis=1))
	SortedZPairs = tf.stack([TmpZ1,TmpZ2],axis=1)
	BondTypeMask = tf.reduce_all(tf.equal(tf.reshape(SortedZPairs, [tf.shape(ZPairs)[0],1,tf.shape(ZPairs)[1]]),tf.reshape(ElemPairs_,[1,nelemp,2])),2)
	rlist = []
	indexlist = []
	num_ele, num_dim = ElemPairs_.get_shape().as_list()
	for e in range(num_ele):
		rlist.append(tf.boolean_mask(RMatrix,BondTypeMask[:,e]))
		indexlist.append(tf.boolean_mask(BndIdxMat,BondTypeMask[:,e]))
	return rlist, indexlist

class ANISym:
	def __init__(self, mset_):
		self.set = mset_
		self.MaxAtoms = self.set.MaxNAtoms()
		self.nmol = len(self.set.mols)
		self.MolPerBatch = 2000
		self.SymOutput = None
		self.xyz_pl= None
		self.Z_pl = None
		self.SFPa = None
		self.SFPr = None
		self.SymGrads = None
		self.TDSSet = None

	def SetANI1Param(self):
		zetas = np.array([[8.0]], dtype = np.float64)
		etas = np.array([[4.0]], dtype = np.float64)
		self.zeta = 8.0
		self.eta = 4.0
		AN1_num_a_As = 8
		thetas = np.array([ 2.0*Pi*i/AN1_num_a_As for i in range (0, AN1_num_a_As)], dtype = np.float64)
		AN1_num_a_Rs = 8
		AN1_a_Rc = 3.1
		self.Ra_cut = 3.1
		self.Rr_cut = 4.6
		rs =  np.array([ AN1_a_Rc*i/AN1_num_a_Rs for i in range (0, AN1_num_a_Rs)], dtype = np.float64)
		Ra_cut = AN1_a_Rc
		# Create a parameter tensor. 4 x nzeta X neta X ntheta X nr
		p1 = np.tile(np.reshape(zetas,[1,1,1,1,1]),[1,1,AN1_num_a_As,AN1_num_a_Rs,1])
		p2 = np.tile(np.reshape(etas,[1,1,1,1,1]),[1,1,AN1_num_a_As,AN1_num_a_Rs,1])
		p3 = np.tile(np.reshape(thetas,[1,1,AN1_num_a_As,1,1]),[1,1,1,AN1_num_a_Rs,1])
		p4 = np.tile(np.reshape(rs,[1,1,1,AN1_num_a_Rs,1]),[1,1,AN1_num_a_As,1,1])
		SFPa = np.concatenate([p1,p2,p3,p4],axis=4)
		self.SFPa = np.transpose(SFPa, [4,0,1,2,3])
		#self.P5 = Tile_P5(1, 1, AN1_num_a_As, AN1_num_a_Rs)

		# Create a parameter tensor. 2 x ntheta X nr
		p1 = np.tile(np.reshape(thetas,[AN1_num_a_As,1,1]),[1,AN1_num_a_Rs,1])
		p2 = np.tile(np.reshape(rs,[1,AN1_num_a_Rs,1]),[AN1_num_a_As,1,1])
		SFPa2 = np.concatenate([p1,p2],axis=2)
		self.SFPa2 = np.transpose(SFPa2, [2,0,1])

		etas_R = np.array([[4.0]], dtype = np.float64)
		AN1_num_r_Rs = 32
		AN1_r_Rc = 4.6
		rs_R =  np.array([ AN1_r_Rc*i/AN1_num_r_Rs for i in range (0, AN1_num_r_Rs)], dtype = np.float64)
		Rr_cut = AN1_r_Rc
		# Create a parameter tensor. 2 x  neta X nr
		p1_R = np.tile(np.reshape(etas_R,[1,1,1]),[1,AN1_num_r_Rs,1])
		p2_R = np.tile(np.reshape(rs_R,[1,AN1_num_r_Rs,1]),[1,1,1])
		SFPr = np.concatenate([p1_R,p2_R],axis=2)
		self.SFPr = np.transpose(SFPr, [2,0,1])
		# Create a parameter tensor. 1  X nr
		p1_new = np.reshape(rs_R,[AN1_num_r_Rs,1])
		self.SFPr2 = np.transpose(p1_new, [1,0])
		#self.P3 = Tile_P3(1,  AN1_num_r_Rs)
		#self.TDSSet = [AllTriplesSet_Np(self.MolPerBatch, self.MaxAtoms), AllDoublesSet_Np(self.MolPerBatch, self.MaxAtoms), AllSinglesSet_Np(self.MolPerBatch, self.MaxAtoms)]


	def Prepare(self):
		"""
		Get placeholders, graph and losses in order to begin training.
		Also assigns the desired padding.

		Args:
		        continue_training: should read the graph variables from a saved checkpoint.
		"""
		with tf.Graph().as_default():
			self.xyz_pl=tf.placeholder(tf.float64, shape=tuple([self.MolPerBatch, self.MaxAtoms,3]))
			self.Z_pl=tf.placeholder(tf.int64, shape=tuple([self.MolPerBatch, self.MaxAtoms]))
			self.Radp_pl=tf.placeholder(tf.int64, shape=tuple([None,3]))
			self.Angt_pl=tf.placeholder(tf.int64, shape=tuple([None,4]))
			Ele = tf.Variable([[1],[8]], dtype = tf.int64)
			Elep = tf.Variable([[1,1],[1,8],[8,8]], dtype = tf.int64)
			#zetas = tf.Variable([[8.0]], dtype = tf.float64)
			#etas = tf.Variable([[4.0]], dtype = tf.float64)
			SFPa = tf.Variable(self.SFPa, tf.float64)
			SFPr = tf.Variable(self.SFPr, tf.float64)
			SFPa2 = tf.Variable(self.SFPa2, tf.float64)
			SFPr2 = tf.Variable(self.SFPr2, tf.float64)
			#P3 = tf.Variable(self.P3, tf.int32)
			#P5 = tf.Variable(self.P5, tf.int32)
			Ra_cut = 3.1
			Rr_cut = 4.6
			#self.Scatter_Sym, self.Sym_Index = TFSymSet_Scattered(self.xyz_pl, self.Z_pl, Ele, SFPr, Rr_cut, Elep, SFPa, Ra_cut)
			#self.Scatter_Sym_Update, self.Sym_Index_Update = TFSymSet_Scattered_Update(self.xyz_pl, self.Z_pl, Ele, SFPr, Rr_cut, Elep, SFPa, Ra_cut)
			#self.Scatter_Sym_Update2, self.Sym_Index_Update2 = TFSymSet_Scattered_Update2(self.xyz_pl, self.Z_pl, Ele, SFPr2, Rr_cut, Elep, SFPa2, self.zeta, self.eta, Ra_cut)
			self.Scatter_Sym_Update, self.Sym_Index_Update = TFSymSet_Scattered_Update_Scatter(self.xyz_pl, self.Z_pl, Ele, SFPr2, Rr_cut, Elep, SFPa2, self.zeta, self.eta, Ra_cut)
			self.Scatter_Sym_Linear, self.Sym_Index_Linear = TFSymSet_Scattered_Linear(self.xyz_pl, self.Z_pl, Ele, SFPr2, Rr_cut, Elep, SFPa2, self.zeta, self.eta, Ra_cut, self.Radp_pl, self.Angt_pl)
			#self.Eee, self.Kern, self.index = TFCoulombCosLR(self.xyz_pl, tf.cast(self.Z_pl, dtype=tf.float64), Rr_cut, self.Radp_pl)
			#self.gradient = tf.gradients(self.Scatter_Sym, self.xyz_pl)
			#self.gradient_update2 = tf.gradients(self.Scatter_Sym_Update2, self.xyz_pl)
			#self.gradient = tf.gradients(self.Scatter_Sym_Update, self.xyz_pl)
			init = tf.global_variables_initializer()
			self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
			self.sess.run(init)
			self.options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
			self.run_metadata = tf.RunMetadata()
		return

	def fill_feed_dict(self, batch_data, coord_pl, atom_pl, radp_pl,  angt_pl):
		return {coord_pl: batch_data[0], atom_pl: batch_data[1], radp_pl:batch_data[2], angt_pl:batch_data[3]}

	def Generate_ANISYM(self):
		xyzs = np.zeros((self.nmol, self.MaxAtoms, 3),dtype=np.float64)
		Zs = np.zeros((self.nmol, self.MaxAtoms), dtype=np.int64)
		nnz_atom = np.zeros((self.nmol), dtype=np.int64)
		random.shuffle(self.set.mols)
		for i, mol in enumerate(self.set.mols):
			xyzs[i][:mol.NAtoms()] = mol.coords
			Zs[i][:mol.NAtoms()] = mol.atoms
			nnz_atom[i] = mol.NAtoms()
		self.SetANI1Param()
		self.Prepare()
		t_total = time.time()
		for i in range (0, int(self.nmol/self.MolPerBatch-1)):
			t = time.time()
			NL = NeighborListSet(xyzs[i*self.MolPerBatch: (i+1)*self.MolPerBatch], nnz_atom[i*self.MolPerBatch: (i+1)*self.MolPerBatch], True, True, Zs[i*self.MolPerBatch: (i+1)*self.MolPerBatch])
			rad_p, ang_t = NL.buildPairsAndTriples(self.Rr_cut, self.Ra_cut)
			print ("time to build pairs:", time.time() - t)
			t = time.time()
			batch_data = [xyzs[i*self.MolPerBatch: (i+1)*self.MolPerBatch], Zs[i*self.MolPerBatch: (i+1)*self.MolPerBatch], rad_p,  ang_t]
			feed_dict = self.fill_feed_dict(batch_data, self.xyz_pl, self.Z_pl, self.Radp_pl, self.Angt_pl)
			t = time.time()
			#sym_output, grad = self.sess.run([self.SymOutput, self.SymGrads], feed_dict = feed_dict)
			#sym_output_update2, sym_index_update2, sym_output, sym_index, gradient_update2 = self.sess.run([self.Scatter_Sym_Update2, self.Sym_Index_Update2, self.Scatter_Sym_Update, self.Sym_Index_Update, self.gradient_update2], feed_dict = feed_dict)
			#sym_output_update, sym_index_update, sym_output, sym_index, gradient, gradient_update = self.sess.run([self.Scatter_Sym_Update, self.Sym_Index_Update, self.Scatter_Sym, self.Sym_Index, self.gradient, self.gradient_update], feed_dict = feed_dict, options=self.options, run_metadata=self.run_metadata)
			#sym_output, sym_index  = self.sess.run([self.Scatter_Sym_Update2, self.Sym_Index_Update2], feed_dict = feed_dict)
			#sym_output, sym_index  = self.sess.run([self.Scatter_Sym, self.Sym_Index], feed_dict = feed_dict, options=self.options, run_metadata=self.run_metadata)
			#A, B  = self.sess.run([self.Scatter_Sym_Update, self.Sym_Index_Update], feed_dict = feed_dict, options=self.options, run_metadata=self.run_metadata)
			A, B, C, D, E, F  = self.sess.run([self.Scatter_Sym_Linear, self.Sym_Index_Linear, self.Scatter_Sym_Update, self.Sym_Index_Update, self.NZT, self.NZT_Linear], feed_dict = feed_dict, options=self.options, run_metadata=self.run_metadata)
			print ("E:\n", E[:50], "\nF:\n", F[:50])
			#print ("i: ", i,  "sym_ouotput: ", len(sym_output)," time:", time.time() - t, " second", "gpu time:", time.time()-t1, sym_index)
			#print ("sym_output_update:", np.array_equal(sym_output_update2[0], sym_output[0]))
			#print ("sym_output_update:", np.sum(np.abs(sym_output_update2[0]-sym_output[0])))
			#print ("gradient_update:", np.sum(np.abs(gradient[0]-gradient_update[0])))
			#print ("sym_index_update:", np.array_equal(sym_index_update[0], sym_index[0]))
			#print ("gradient:", gradient[0].shape)
			fetched_timeline = timeline.Timeline(self.run_metadata.step_stats)
			chrome_trace = fetched_timeline.generate_chrome_trace_format()
			with open('timeline_step_%d_old.json' % i, 'w') as f:
				f.write(chrome_trace)
			print ("inference time:", time.time() - t)
