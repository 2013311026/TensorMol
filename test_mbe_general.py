from Util import *
from Sets import *
from TensorMolData import *
from TFMolManage import *
from MolDigest import *
from NN_MBE import *
from NN_Opt import *


# steps to train a NN-MBE model
if (1):
	#Load .xyz files.
	if (1):
		#a=MSet("NaCl_H2O_NaH2Ogroup") # Define our set.
		a=MSet("H2O_936_NaCl_88") # Define our set.
		#a.ReadGDB9Unpacked("./NaCl_H2O_NaH2Ogroup/") # Load .xyz file into set and set maxinum many-body expansion order.
		a.ReadGDB9Unpacked("./H2O_936_NaCl_88/") # Load .xyz file into set and set maxinum many-body expansion order.
		a.Generate_All_Pairs(pair_list=[{"pair":"NaCl", "mono":["Na","Cl"], "center":[0,0]}])
		#a.Generate_All_MBE_term_General([{"atom":"OHHNa", "charge":1}, {"atom":"OHHCl", "charge":-1},{"atom":"OHH", "charge":0}], cutoff=10, center_atom=[0,0,0]) # Generate all the many-body terms with  certain radius cutoff.
		a.Generate_All_MBE_term_General([{"atom":"OHH", "charge":0}, {"atom":"NaCl", "charge":0}], cutoff=10, center_atom=[0, -1]) # Generate all the many-body terms with  certain radius cutoff.  # -1 means center of mass

		# One can also load another set and combine with orginal one.
		#b=MSet("He2")   
                #b.ReadGDB9Unpacked("./He2/", mbe_order=2)
		#b.Generate_All_MBE_term(atom_group=1, cutoff=4, center_atom=0)
                #a.CombineSet(b) 

		#a.Save() # Save the training set, by default it is saved in ./datasets.

	#Calculate the MP2 many-body energies.
	if (0):
		#a=MSet("NaCl_H2O_NaH2Ogroup") 
		a=MSet("NaCl_H2O_NaClgroup")  
		a.Load() # Load generated training set (.pdb file).
		#a.Calculate_All_Frag_Energy_General(method="qchem")  # Use PySCF or Qchem to calcuate the MP2 many-body energy of each order.
		a.Get_All_Qchem_Frag_Energy_General()
		a.Save() 

	# Do the permutation if it is necessary.
	if (0):
		a=MSet("H2O_tinker_amoeba")
		a.Load()
		a.Get_Permute_Frags(indis=[1,2]) # Include all the possible permutations of each fragment.
		a.Save()

	# Prepare data for neural newtork training.
	if (0):
		a=MSet("H2O_tinker_amoeba")
                a.Load()
		TreatedAtoms = a.AtomTypes()
		print "TreatedAtoms ", TreatedAtoms 
		d = MolDigester(TreatedAtoms, name_="SymFunc")  # Initialize a digester that apply descriptor for the fragments.
		#tset = TensorMolData(a,d, order_=2, num_indis_=2) # Initialize TensorMolData that contain the training data for the neural network for certain order of many-body expansion.
		#tset.BuildTrain("H2O_tinker_amoeba") # Genearte training data with the loaded molecule set and the chosen digester, by default it is saved in ./trainsets.
		tset = TensorMolData_BP(a,d, order_=2, num_indis_=2) # Initialize TensorMolData that contain the training data for the neural network for certain order of many-body expansion.
		tset.BuildTrain("H2O_tinker_amoeba")

	# doing the KRR for the set for debug purpose.
	if (0):
		tset = TensorMolData_BP(MSet(),MolDigester([]),"H2O_tinker_amoeba_GauInv_1") # Load the generated data for training the neural network.
		tset.KRR()
	
	# testing the BP TensorMolData
	if (0):
                tset = TensorMolData_BP(MSet(),MolDigester([]),"H2O_tinker_amoeba_SymFunc_1")
		#tset.LoadDataToScratch(True)

	# Train the neural network.
	if (0):
		tset = TensorMolData_BP(MSet(),MolDigester([]),"H2O_tinker_amoeba_SymFunc_2") # Load the generated data for training the neural network.
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP") # Initialzie a manager than manage the training of neural network.
		manager.Train(maxstep=20000)  # train the neural network for 500 steps, by default it trainse 10000 steps and saved in ./networks.

	# Test the neural network.
	if (0):
		manager = TFMolManage("H2O_tinker_amoebaCoulomb_fc_sqdiff_2", None, False) # Load pre-trained network.	
		manager.Test("nn_acc_pred.dat") # Save the test result of our trained network. 


# steps to evaluate the many-body energy using  NN-MBE model
if (0):
	# load molecule
	a=MSet("H2O_opt")
	a.ReadGDB9Unpacked("./H2O_opt/")
	# load pre-trained networks {many-body order: network name}
	tfm = {1:"H2O_tinker_amoebaCoulomb_fc_sqdiff_1", 2:"H2O_tinker_amoebaCoulomb_fc_sqdiff_2"}
	# launch NN-MBE model 
	nn_mbe = NN_MBE(tfm)
	# evaluate using NN-MBE model 
	for mol in a.mols:
		#mol.Generate_All_MBE_term(atom_group=3, cutoff=5, center_atom=0)   
		nn_mbe.NN_Energy(mol)

# use NN-MBE model to optimize molecule. 
if (0):
	# load molecule
        a=MSet("H2O_opt")
        a.ReadGDB9Unpacked("./H2O_opt/")
        # load pre-trained networks {many-body order: network name}
        tfm = {1:"H2O_tinker_amoebaCoulomb_fc_sqdiff_1", 2:"H2O_tinker_amoebaCoulomb_fc_sqdiff_2"}
        # launch NN-MBE model 
        nn_mbe = NN_MBE(tfm)
	# launch Optimizer
        opt=NN_Optimizer(nn_mbe)
	# Optimize
        for mol in a.mols:
		#mol.Generate_All_MBE_term(atom_group=3, cutoff=5, center_atom=0)
		#opt.NN_Opt(mol)
        	opt.NN_LBFGS_Opt(mol)
