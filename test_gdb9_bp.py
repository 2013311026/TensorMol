from Util import *
from Sets import *
from TensorMolData import *
from TFMolManage import *
from MolDigest import *
from NN_MBE import *
from NN_Opt import *

# John's tests
if (1):
	# To read gdb9 xyz files and populate an Mset.
	# Because we use pickle to save. if you write new routines on Mol you need to re-execute this.
	if (0):
		a=MSet("gdb9")
		a.ReadGDB9Unpacked("/home/kyao/TensorMol/gdb9/")
		allowed_eles=[1, 6, 8]
                a.CutSet(allowed_eles)
		a.Save()
		#a.Load()
		#b=MSet("OptMols")
		#b.ReadXYZ("OptMols")
		#b.Save()
		#c=a.DistortedClone()
		#c.Save()
		#d=b.DistortedClone()
		#d.Save()

	# To generate training data for all the atoms in the GDB 9
	if (0):
		# 1 - Get molecules into memory
		a=MSet("gdb9_1_6_8")
                a.Load()
                TreatedAtoms = a.AtomTypes()
                print "TreatedAtoms ", TreatedAtoms
                d = MolDigester(TreatedAtoms, name_="Coulomb_BP")  # Initialize a digester that apply descriptor for the fragments.
                #tset = TensorMolData(a,d, order_=2, num_indis_=2) # Initialize TensorMolData that contain the training data for the neural network for certain order of many-body expansion.
                #tset.BuildTrain("H2O_tinker_amoeba") # Genearte training data with the loaded molecule set and the chosen digester, by default it is saved in ./trainsets.
                tset = TensorMolData_BP(a,d, order_=1, num_indis_=1, type_="mol") # Initialize TensorMolData that contain the training data for the neural network for certain order of many-body expansion.
                tset.BuildTrain("gdb9_1_6_8")

	if (1):
         	tset = TensorMolData_BP(MSet(),MolDigester([]),"gdb9_1_6_8_Coulomb_BP_1")
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP") # Initialzie a manager than manage the training of neural network.
                manager.Train(maxstep=20000)  # train the neural network for 500 steps, by default it trainse 10000 steps and saved in ./networks.

	# This Trains the networks.
	if (0):
		tset = TensorData(None,None,"gdb9_NEQ_SensoryBasis")
		manager=TFManage("",tset,True,"fc_sqdiff") # True indicates train all atoms

# Kun's tests.
if (0):
	if (0):
		a=MSet("C2H6")
		#a.ReadXYZ("CxHy_test")
		a.ReadGDB9Unpacked("./C2H6/")
		#a.Save()
	#	a=MSet("gdb9_NEQ")
	#	a.Load()
		#b=MSet("gdb9")
		#b.Load()
		#allowed_eles=[1, 6]
		#b.CutSet(allowed_eles)
		#print "length of bmols:", len(b.mols)
		a = a.DistortedClone(100000)
		a.Save()

	if (0):
		#a=MSet("CxHy_test_NEQ")
		#a.Load()
		a=MSet("gdb9_1_6_NEQ")
	  	#a=a.DistortedClone(1)	
		a.Load()	
		# Choose allowed atoms.
		TreatedAtoms = a.AtomTypes()
		#for mol in a.mols:
		#	mol.BuildDistanceMatrix()
		# 2 - Choose Digester
		#d = Digester(TreatedAtoms, name_="SymFunc",OType_ ="Force")
		#d.TrainDigestW(a.mols[0], 6)
		print "len of amols", len(a.mols)
		d = Digester(TreatedAtoms, name_="PGaussian",OType_ ="GoForce_old_version", SamplingType_="None")
		#d.Emb(a.mols[0],0, np.zeros((1,3)))
		#d.Emb(a.mols[0],0, a.mols[0].coords[0].reshape(1,-1))
		#4 - Generate training set samples.

	if (0):
		tset = TensorData(a,d)
		tset.BuildTrain("gdb9_1_6_NEQ",TreatedAtoms) # generates dataset numpy arrays for each atom.

	if (1):
		tset = TensorData(MSet(),Digester([]),"gdb9_1_6_NEQ_PGaussian")
		#tset_test = TensorData(MSet(),Digester([]),"CxHy_test_SymFunc") 
		#manager=TFManage("",tset,False,"fc_sqdiff", tset_test) # True indicates train all atoms.
		manager=TFManage("",tset,False,"fc_sqdiff")
		manager.TrainElement(6)
		#tset = TensorData(MSet(),Digester([]),"gdb9_1_6_NEQ_SymFunc")
		#manager = TFManage("", tset , True)
	
	if (0):
		a=MSet("C2H6_NEQ")
                a.Load()
		optimizer  = Optimizer(None)
		optimizer.GoOpt(a.mols[0])


# This visualizes the go potential and projections on to basis vectors.
if (0):
	a=MSet("OptMols")
	a.Load()
	m = a.mols[0]
	#m.BuildDistanceMatrix()
	m.Distort(0,2.0);
	# I did this just to look at the go prob of morphine for various distortions... it looks good and optimizes.
	if (0):
		#   Try dumping these potentials onto the sensory atom, and seeing how that works...
		#   It worked poorly for atom centered basis, but a grid of gaussians was great.
		for i in range(1,m.NAtoms()):
			m.FitGoProb(i)
		samps, vol = m.SpanningGrid(150,2)
		Ps = m.POfAtomMoves(samps,0)
		for i in range(1,m.NAtoms()):
			Ps += m.POfAtomMoves(samps,i)
		Ps /= Ps.max()
		Ps *= 254.0
		m.GridstoRaw(Ps,150,"Morphine")
	# Attempt an optimization to check that mean-probability will work if it's perfectly predicted.
	if (0):
		optimizer  = Optimizer(None)
		optimizer.GoOptProb(m) # This works perfectly.

# This draws test volumes for Morphine
if (0):
	a=MSet("OptMols")
	a.Load()
	test_mol = a.mols[0]
	manager=TFManage("gdb9_NEQ_SymFunc",None,False)
	xyz,p = manager.EvalAllAtoms(test_mol)
	grids = test_mol.MolDots()
	grids = test_mol.AddPointstoMolDots(grids, xyz, p)
	np.savetxt("./densities/morph.xyz",test_mol.coords)
	test_mol.GridstoRaw(grids,250,"Morphine")


# This tests the optimizer.
if (0):
#	a=MSet()
	a=MSet("OptMols")
	a.Load()
	test_mol = a.mols[0]
	test_mol.DistortedCopy(0.2)
	print test_mol.coords
	print test_mol.atoms
	manager=TFManage("gdb9Coulomb",None,False)
	optimizer  = Optimizer(manager)
	optimizer.Opt(test_mol)

# This is for test of c2h6, c2h4, c2h2
if (0):
	c2h6 = np.loadtxt("c2h4.xyz")
	atoms = (c2h6[:,0].reshape(c2h6.shape[0])).copy()
	atoms = np.array(atoms, dtype=np.uint8)
	coords = c2h6[:, 1:4].copy()
	test_mol =Mol(atoms, coords)
#        print  test_mol.coords, test_mol.atoms
	manager=TFManage("gdb9SymFunc",None,False)
	optimizer  = Optimizer(manager)
	optimizer.Opt(test_mol)

# This tests the GO-Model potential.
if (0):
#	a=MSet()
	a=MSet("OptMols")
	a.Load()
	test_mol = (a.mols)[1]
	print test_mol.coords
	test_mol.Distort(0.3)
	print test_mol.coords
	print test_mol.atoms
	optimizer  = Optimizer(None)
	optimizer.GoOpt(test_mol)
#	optimizer.GoOpt_ScanForce(test_mol)

# this generates uniform samples of morphine for me. 
if (0):
	a=MSet("OptMols")
	a.Load()
	TreatedAtoms = a.AtomTypes()
	d = Digester(TreatedAtoms)
	tset = TensorData(a,d,None)
	tset.BuildSamples("Test",[],True)
