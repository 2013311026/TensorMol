#
# A molecule set is not a training set.
#

from Mol import *
from Util import *
import numpy as np
import os,sys,pickle,re,copy,time 

class MSet:
	""" A molecular database which 
		provides structures """
	def __init__(self, name_ ="gdb9", path_="./datasets/"):
		self.mols=[]
		self.path=path_
		self.name=name_
		self.suffix=".pdb" #Pickle Database? Poor choice.

	def Save(self):
		print "Saving set to: ", self.path+self.name+self.suffix
		f=open(self.path+self.name+self.suffix,"wb")
		pickle.dump(self.__dict__, f, protocol=1)
		f.close()
		return

	def Load(self):
		f = open(self.path+self.name+self.suffix,"rb")
		tmp=pickle.load(f)
		self.__dict__.update(tmp)
		f.close()
		print "Loaded, ", len(self.mols), " molecules "
		print self.NAtoms(), " Atoms total"
		print self.AtomTypes(), " Types "
		return

	def DistortedClone(self, NDistorts=1, random=True):
		''' Create a distorted copy of a set'''
		print "Making distorted clone of:", self.name
		s = MSet(self.name+"_NEQ")
		ord = range(len(self.mols))
		if(random):
			np.random.seed(int(time.time()))
			ord=np.random.permutation(len(self.mols))
		for j in ord: 
			for i in range (0, NDistorts):
				s.mols.append(copy.deepcopy(self.mols[j]))
				s.mols[-1].Distort()
		return s
	
	def TransformedClone(self, transf_num):
		''' make a linearly transformed copy of a set. '''
		print "Making distorted clone of:", self.name
		s = MSet(self.name+"_transf_"+str(transf_num))
		ord = range(len(self.mols))
		for j in ord:
				s.mols.append(copy.deepcopy(self.mols[j]))
				s.mols[-1].Transform(GRIDS.InvIsometries[transf_num])
		return s

	def NAtoms(self):
		nat=0
		for m in self.mols:
			nat += m.NAtoms()
		return nat

	def AtomTypes(self):
		types = np.array([],dtype=np.uint8)
		for m in self.mols:
			types = np.union1d(types,m.AtomTypes())
		return types

	def ReadGDB9Unpacked(self, path="/Users/johnparkhill/gdb9/"):
		""" Reads the GDB9 dataset as a pickled list of molecules"""
		from os import listdir
		from os.path import isfile, join
		onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
		for file in onlyfiles:
			if ( file[-4:]!='.xyz' ):
				continue
			self.mols.append(Mol())
			self.mols[-1].ReadGDB9(path+file)
		return

	def ReadXYZ(self,filename):
		""" Reads XYZs concatenated into a single separated by \n\n file as a molset """
		f = open(self.path+filename+".xyz","r")
		txts = f.readlines()
		for line in range(len(txts)):
			if (txts[line].count('Comment:')>0):
				line0=line-1
				nlines=int(txts[line0])
				self.mols.append(Mol())
				self.mols[-1].FromXYZString(''.join(txts[line0:line0+nlines+2]))
		return

	def WriteXYZ(self,filename=None):
		if filename == None:
			filename = self.name
		for mol in self.mols:
			mol.WriteXYZfile(self.path,filename)
		return

	def pop(self, ntopop):
		for i in range(ntopop):
			self.mols.pop()
		return

	def OnlyWithElements(self, allowed_eles):
		mols=[]
		for mol in self.mols:
			if set(list(mol.atoms)).issubset(allowed_eles):
				mols.append(mol)
		for i in allowed_eles:
			self.name += "_"+str(i)
		self.mols=mols
		return
	
	def CombineSet(self, b, name_=None):
		if name_ == None:
			self.name = self.name + b.name
		self.mols.append(b.mols) 
		return
		
	def MBE(self,  atom_group=1, cutoff=10, center_atom=0):
		for mol in self.mols:
			mol.MBE(atom_group, cutoff, center_atom)		
		return  

	def PySCF_Energy(self):
		for mol in self.mols:
			mol.PySCF_Energy()
		return 	
	

	def Generate_All_MBE_term(self,  atom_group=1, cutoff=10, center_atom=0):
		for mol in self.mols:
                	mol.Generate_All_MBE_term(atom_group, cutoff, center_atom)
                return 
	
	def Calculate_All_Frag_Energy(self, method="pyscf"):
		for mol in self.mols:
			mol.Calculate_All_Frag_Energy(method)
               # 	mol.Set_MBE_Energy()
		return


	def Get_All_Qchem_Frag_Energy(self):
		for mol in self.mols:
			mol.Get_All_Qchem_Frag_Energy()
		return 
	
	def Get_Permute_Frags(self, indis=[0]):
		for mol in self.mols:
			mol.Get_Permute_Frags(indis)
		return  
