from TensorMol import *
import time
PARAMS["max_checkpoints"] = 3
os.environ["CUDA_VISIBLE_DEVICES"]="0"


# Takes two nearly identical crystal lattices and interpolates a core/shell structure, must be oriented identically and stoichiometric
def InterpolateGeometries():
	a=MSet('cspbbr3_tess')
	#a.ReadGDB9Unpacked(path='/media/sdb2/jeherr/TensorMol/datasets/cspbbr3/pb_tess_6sc/')
	#a.Save()
	a.Load()
	mol1 = a.mols[0]
	mol2 = a.mols[1]
	mol2.RotateX()
	mol1.AlignAtoms(mol2)
	optimizer = Optimizer(None)
	optimizer.Interpolate_OptForce(mol1, mol2)
	mol1.WriteXYZfile(fpath='./results/cspbbr3_tess', fname='cspbbr3_6sc_pb_tess_goopt', mode='w')
	# mol2.WriteXYZfile(fpath='./results/cspbbr3_tess', fname='cspbbr3_6sc_ortho_rot', mode='w')

def ReadSmallMols(set_="SmallMols", dir_="/media/sdb2/jeherr/TensorMol/datasets/small_mol_dataset/*/*/", energy=False, forces=False, charges=False, mmff94=False):
	import glob
	a=MSet(set_)
	for dir in glob.iglob(dir_):
		a.ReadXYZUnpacked(dir, has_force=forces, has_energy=energy, has_charge=charges, has_mmff94=mmff94)
	print len(a.mols), " Molecules"
	a.Save()


def TrainKRR(set_ = "SmallMols", dig_ = "GauSH", OType_ ="Force"):
	a=MSet("SmallMols_rand")
	a.Load()
	TreatedAtoms = a.AtomTypes()
	d = Digester(TreatedAtoms, name_=dig_,OType_ =OType_)
	tset = TensorData(a,d)
	tset.BuildTrainMolwise("SmallMols",TreatedAtoms)
	manager=TFManage("",tset,True,"KRR_sqdiff")
	return

def RandomSmallSet(set_, size_):
	""" Returns an MSet of random molecules chosen from a larger set """
	print "Selecting a subset of "+str(set_)+" of size "+str(size_)
	a=MSet(set_)
	a.Load()
	b=MSet(set_+"_rand")
	mols = random.sample(range(len(a.mols)), size_)
	for i in mols:
		b.mols.append(a.mols[i])
	b.Save()
	return b

def BasisOpt_KRR(method_, set_, dig_, OType = None, Elements_ = []):
	""" Optimizes a basis based on Kernel Ridge Regression """
	a=MSet(set_)
	a.Load()
	TreatedAtoms = a.AtomTypes()
	dig = Digester(TreatedAtoms, name_=dig_, OType_ = OType)
	eopt = EmbeddingOptimizer(method_, a, dig, OType, Elements_)
	eopt.PerformOptimization()
	return

def BasisOpt_Ipecac(method_, set_, dig_):
	""" Optimizes a basis based on Ipecac """
	a=MSet(set_)
	a.Load()
	print "Number of mols: ", len(a.mols)
	TreatedAtoms = a.AtomTypes()
	dig = MolDigester(TreatedAtoms, name_=dig_, OType_ ="GoForce")
	eopt = EmbeddingOptimizer("Ipecac", a, dig, "radial")
	eopt.PerformOptimization()
	return

def TestIpecac(dig_ = "GauSH"):
	""" Tests reversal of an embedding type """
	a=MSet("OptMols")
	a.ReadXYZ("OptMols")
	m = a.mols[1]
	print m.atoms
	# m.WriteXYZfile("./results/", "Before")
	goodcrds = m.coords.copy()
	m.BuildDistanceMatrix()
	gooddmat = m.DistMatrix
	print "Good Coordinates", goodcrds
	TreatedAtoms = m.AtomTypes()
	dig = MolDigester(TreatedAtoms, name_=dig_, OType_ ="GoForce")
	emb = dig.Emb(m, MakeOutputs=False)
	m.Distort()
	ip = Ipecac(a, dig, eles_=[1,6,7,8])
	# m.WriteXYZfile("./results/", "Distorted")
	bestfit = ip.ReverseAtomwiseEmbedding(emb, atoms_=m.atoms, guess_=m.coords,GdDistMatrix=gooddmat)
	# bestfit = ReverseAtomwiseEmbedding(dig, emb, atoms_=m.atoms, guess_=None,GdDistMatrix=gooddmat)
	# print bestfit.atoms
	print m.atoms
	# bestfit.WriteXYZfile("./results/", "BestFit")
	return

def TrainForces(set_ = "SmallMols", dig_ = "GauSH", BuildTrain_=True, numrot_=None):
	if (BuildTrain_):
		a=MSet(set_)
		a.Load()
		if numrot_ != None:
			a = a.RotatedClone(numrot_)
			a.Save(a.name+"_"+str(numrot_)+"rot")
		TreatedAtoms = a.AtomTypes()
		print "Number of Mols: ", len(a.mols)
		d = Digester(TreatedAtoms, name_=dig_, OType_="Force")
		tset = TensorData(a,d)
		tset.BuildTrainMolwise(set_,TreatedAtoms)
	else:
		tset = TensorData(None,None,set_+"_"+dig_)
	manager=TFManage("",tset,False,"fc_sqdiff")
	manager.TrainElement(1)

def OptTFForces(set_= "SmallMols", dig_ = "GauSH", mol = 0):
	a=MSet(set_)
	a.ReadXYZ()
	tmol=copy.deepcopy(a.mols[mol])
	# tmol.Distort(0.1)
	manager=TFManage("SmallMols_20rot_"+dig_+"_"+"fc_sqdiff", None, False)
	opt=Optimizer(manager)
	opt.OptTFRealForce(tmol)

def TestOCSDB(dig_ = "GauSH", net_ = "fc_sqdiff"):
	"""
	Test John Herr's first Optimized Force Network.
	OCSDB_test contains good crystal structures.
	- Evaluate RMS forces on them.
	- Optimize OCSDB_Dist02
	- Evaluate the relative RMS's of these two.
	"""
	tfm=TFManage("SmallMols_20rot_"+dig_+"_"+net_,None,False)
	a=MSet("OCSDB_Dist02_opt")
	a.ReadXYZ()
	b=MSet("OCSDB_Dist02_opt_test")
	b.mols = copy.deepcopy(a.mols)
	for m in b.mols:
		m.Distort(0.1)
	print "A,B RMS (Angstrom): ",a.rms(b)
	frcs = np.zeros(shape=(1,3))
	for m in a.mols:
		frc = tfm.EvalRotAvForce(m, RotAv=PARAMS["RotAvOutputs"], Debug=False)
		frcs=np.append(frcs,frc,axis=0)
	print "RMS Force of crystal structures:",np.sqrt(np.sum(frcs*frcs,axis=(0,1))/(frcs.shape[0]-1))
	b.name = "OCSDB_Dist02_OPTd"
	optimizer  = Optimizer(tfm)
	for i,m in enumerate(b.mols):
		m = optimizer.OptTFRealForce(m,str(i))
	b.WriteXYZ()
	print "A,B (optd) RMS (Angstrom): ",a.rms(b)
	return

def TestNeb(dig_ = "GauSH", net_ = "fc_sqdiff"):
	"""
	Test NudgedElasticBand
	"""
	tfm=TFManage("SmallMols_20rot_"+dig_+"_"+net_,None,False)
	optimizer  = Optimizer(tfm)
	a=MSet("NEB_Berg")
	a.ReadXYZ("NEB_Berg")
	m0 = a.mols[0]
	m1 = a.mols[1]
	# These have to be aligned and optimized if you want a good PES.
	m0.AlignAtoms(m1)
	m0 = optimizer.OptTFRealForce(m0,"NebOptM0")
	m1 = optimizer.OptTFRealForce(m1,"NebOptM1")
	PARAMS["NebNumBeads"] = 30
	PARAMS["NebK"] = 2.0
	PARAMS["OptStepSize"] = 0.002
	PARAMS["OptMomentum"] = 0.0
	PARAMS["OptMomentumDecay"] = 1.0
	neb = NudgedElasticBand(tfm, m0, m1)
	neb.OptNeb()
	return

def Brute_LJParams():
	a=MSet("SmallMols_rand")
	a.Load()
	TreatedAtoms = a.AtomTypes()
	d = MolDigester(TreatedAtoms, name_="CZ", OType_ ="Energy")
	tset = TensorMolData(a,d)
	ins = MolInstance_DirectForce_tmp(tset,None,False,"Harm")
	ins.train_prepare()
	import scipy.optimize
	rranges = (slice(-1000, 1000, 10), slice(0.5, 6, 0.25))
	resbrute = scipy.optimize.brute(ins.LJFrc, rranges, full_output=True, finish=scipy.optimize.fmin)
	print resbrute[0]
	print resbrute[1]
	# print ins.LJFrc(p)

def QueueTrainForces(trainset_ = "SmallMols_train", testset_ = "SmallMols_test", dig_ = "GauSH", BuildTrain_=True, numrot_=None):
	if (BuildTrain_):
		a=MSet(trainset_)
		a.Load()
		b=MSet(testset_)
		b.Load()
		if numrot_ != None:
			a = a.RotatedClone(numrot_)
			a.Save(a.name+"_"+str(numrot_)+"rot")
		TreatedAtoms = a.AtomTypes()
		print "Number of Mols: ", len(a.mols)
		d = Digester(TreatedAtoms, name_=dig_, OType_="Force")
		tset = TensorData_TFRecords(a,d)
		tset.BuildTrainMolwise(set_,TreatedAtoms)
	else:
		trainset = TensorData_TFRecords(None,None,trainset_+"_"+dig_)
		testset = TensorData_TFRecords(None, None,testset_+"_"+dig_)
	manager=TFManage_Queue("",trainset, testset, False,"fc_sqdiff_queue")
	manager.TrainElement(1)

def TestForces():
	a=MSet("chemspid")
	# a=MSet("SmallMols")
	a.Load()
	manager=TFManage("SmallMols_GauSH_fc_sqdiff", None, False)
	err = np.zeros((32000,3))
	ntest = 0
	for mol in a.mols:
		for i, atom in enumerate(mol.atoms):
			if atom == 7:
				pforce = manager.evaluate(mol, i)
				print "True force:", mol.properties["forces"][i], "Predicted force:", pforce
				err[ntest] = mol.properties["forces"][i] - pforce
				ntest += 1
				if ntest == 32000:
					break
		if ntest == 32000:
			break
	print "MAE:", np.mean(np.abs(err)), " Std:", np.std(np.abs(err))
	# print err

def MakeTestSet():
	b=MSet("SmallMols_train")
	b.Load()
	# c=MSet("SmallMols_test")
	# c.Load()
	TreatedAtoms = b.AtomTypes()
	print "Number of train Mols: ", len(b.mols)
	# print "Number of test Mols: ", len(c.mols)
	d = Digester(TreatedAtoms, name_="GauSH", OType_="Force")
	train_set = TensorData_TFRecords(b,d)
	train_set.BuildTrainMolwise("SmallMols_train",TreatedAtoms)
	# test_set = TensorData_TFRecords(c,d, test_=True)
	# test_set.BuildTrainMolwise("SmallMols_test",TreatedAtoms)

def TestMetadynamics():
	a = MSet("MDTrajectoryMetaMD")
	a.ReadXYZ()
	m = a.mols[0]
	ForceField = lambda x: QchemDFT(Mol(m.atoms,x),basis_ = '6-311g**',xc_='wB97X-D', jobtype_='force', filename_='jmols2', path_='./qchem/', threads=8)
	masses = np.array(map(lambda x: ATOMICMASSESAMU[x-1],m.atoms))
	print "Masses:", masses
	PARAMS["MDdt"] = 2.0
	PARAMS["RemoveInvariant"]=True
	PARAMS["MDMaxStep"] = 200
	PARAMS["MDThermostat"] = "Nose"
	PARAMS["MDTemp"]= 600.0
	meta = MetaDynamics(ForceField, m)
	meta.Prop()

def TestTFBond():
	a=MSet("chemspider_all_rand")
	a.Load()
	d = MolDigester(a.BondTypes(), name_="CZ", OType_="AtomizationEnergy")
	tset = TensorMolData_BPBond_Direct(a,d)
	manager=TFMolManage("",tset,True,"fc_sqdiff_BPBond_Direct")

def GetPairPotential():
	manager=TFMolManage("Mol_SmallMols_rand_CZ_fc_sqdiff_BPBond_Direct_1", Trainable_ = False)
	PairPotVals = manager.EvalBPPairPotential()
	for i in range(len(PairPotVals)):
		np.savetxt("PairPotentialValues_elempair_"+str(i)+".dat",PairPotVals[i])

def TestTFGauSH():
	np.set_printoptions(threshold=100000)
	a=MSet("SmallMols_rand")
	a.Load()
	maxnatoms = a.MaxNAtoms()
	zlist = []
	xyzlist = []
	labelslist = []
	for i, mol in enumerate(a.mols):
		paddedxyz = np.zeros((maxnatoms,3), dtype=np.float32)
		paddedxyz[:mol.atoms.shape[0]] = mol.coords
		paddedlabels = np.zeros((maxnatoms, 3), dtype=np.float32)
		paddedlabels[:mol.atoms.shape[0]] = mol.properties["forces"]
		xyzlist.append(paddedxyz)
		labelslist.append(paddedlabels)
		if i == 1:
			break
	xyzstack = tf.stack(xyzlist)
	labelstack = tf.stack(labelslist)
	tmp = TF_random_rotate(xyzstack, labelstack)
	sess = tf.Session()
	for i in range(a.mols[0].atoms.shape[0]):
		print a.mols[0].atoms[i], "   ", a.mols[0].coords[i,0], "   ", a.mols[0].coords[i,1], "   ", a.mols[0].coords[i,2]
	new_xyzs, new_labels = sess.run(tmp)
	print new_xyzs[0]

def train_forces_GauSH_direct(set_ = "SmallMols"):
	PARAMS["RBFS"] = np.array([[0.14281105, 0.25747465], [0.24853184, 0.38609822], [0.64242406, 0.36870154], [0.97548212, 0.39012401],
	 							[1.08681976, 0.25805578], [1.34504847, 0.16033599], [1.49612151, 0.31475267], [1.91356037, 0.52652435],
								[2.35, 0.8], [2.8, 0.8], [3.25, 0.8], [3.7, 0.8], [4.15, 0.8], [4.6, 0.8], [5.05, 0.8], [5.5, 0.8], [5.95, 0.8],
								[6.4, 0.8], [6.6, 2.4], [8.8, 2.4], [11., 2.4], [13.2,2.4], [15.4, 2.4]])
	PARAMS["ANES"] = np.array([1.02539286, 1.0, 1.0, 1.0, 1.0, 2.18925953, 2.71734044, 3.03417733])
	PARAMS["SH_NRAD"] = 14
	PARAMS["SH_LMAX"] = 4
	PARAMS["SRBF"] = MatrixPower(MolEmb.Overlap_RBF(PARAMS),-1./2)
	PARAMS["HiddenLayers"] = [512, 512, 512, 512]
	PARAMS["max_steps"] = 2000
	PARAMS["test_freq"] = 5
	PARAMS["batch_size"] = 2000
	PARAMS["NeuronType"] = "elu"
	PARAMS["tf_prec"] = "tf.float64"
	a=MSet(set_)
	a.Load()
	TreatedAtoms = a.AtomTypes()
	print "Number of Mols: ", len(a.mols)
	d = Digester(TreatedAtoms, name_="GauSH", OType_="Force")
	tset = TensorDataDirect(a,d)
	manager=TFManage("",tset,True,"fc_sqdiff_GauSH_direct")


# InterpoleGeometries()
# ReadSmallMols(set_="SmallMols", forces=True, energy=True)
# ReadSmallMols(set_="chemspider3", dir_="/media/sdb2/jeherr/TensorMol/datasets/chemspider3_data/*/", energy=True, forces=True)
# TrainKRR(set_="SmallMols_rand", dig_ = "GauSH", OType_="Force")
# RandomSmallSet("chemspider_all_60", 500000)
# BasisOpt_KRR("KRR", "SmallMols_rand", "GauSH", OType = "Force", Elements_ = [1,6,7,8])
# BasisOpt_Ipecac("KRR", "ammonia_rand", "GauSH")
# TestIpecac()
# TrainForces(set_ = "SmallMols", BuildTrain_=False, numrot_=1)
# OptTFForces(set_ = "peptide", mol=0)
# TestOCSDB()
# Brute_LJParams()
# QueueTrainForces(trainset_ = "SmallMols_train", testset_ = "SmallMols_test", BuildTrain_=False, numrot_=None)
# TestForces()
# MakeTestSet()
# BIMNN_NEq()
# TestMetadynamics()
# TestMD()
# TestTFBond()
# GetPairPotential()
# TestTFGauSH()
train_forces_GauSH_direct("SmallMols_rand")
