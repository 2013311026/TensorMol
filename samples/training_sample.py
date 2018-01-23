from __future__ import absolute_import
from TensorMol import *
import os
os.environ["CUDA_VISIBLE_DEVICES"]="2" # Choose your GPU, here is set to use CPU
from TensorMol.Interfaces.TMIPIinterface import *
import random

def Train():
	if (1):   # learning energy and gradient
	# energy should be in hartree, gradient should be in hartree/angstrom
		a = MSet("water_mini") # water_mini.pdb is in folder "./datasets/"
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "training_sample"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 15 # Train for 5 epochs in total
		PARAMS["batch_size"] =  100
		PARAMS["test_freq"] = 1 # Test for every epoch
		PARAMS["tf_prec"] = "tf.float64" # double precsion
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["NeuronType"] = "sigmoid_with_param" # choose activation function
		PARAMS["sigmoid_alpha"] = 100.0  # activation params
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0] # each layer's keep probability for dropout
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="AtomizationEnergy")
		tset = TensorMolData_BP_Direct_EandG_Release(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EandG_SymFunction")
		PARAMS['Profiling']=0
		manager.Train(1)

	if (0): # learning energy, gradient and dipole
	# energy should be in hartree, gradient should be in hartree/angstrom, dipole should be in a.u.
		a = MSet("water_mini") # water_mini.pdb is in folder "./datasets/"
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "training_sample"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 15 # Train for 5 epochs in total
		PARAMS["batch_size"] =  100
		PARAMS["test_freq"] = 1 # Test for every epoch
		PARAMS["tf_prec"] = "tf.float64" # double precsion
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"] = 1.0
		PARAMS["NeuronType"] = "sigmoid_with_param" # choose activation function
		PARAMS["sigmoid_alpha"] = 100.0  # activation params
		PARAMS["HiddenLayers"] = [100, 100, 100]  # number of neurons in each layer
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0] # each layer's keep probability for dropout
		PARAMS["learning_rate_dipole"] = 0.0001  # learning rate for dipole learning
		PARAMS["learning_rate_energy"] = 0.00001 # learning rate for energy & grads learning
		PARAMS["SwitchEpoch"] = 5  # Train dipole for 2 epochs, then train energy & grads
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")
		tset = TensorMolData_BP_Direct_EE_WithEle_Release(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_SymFunction")
		PARAMS['Profiling']=0
		manager.Train(1)


def Eval():
	if (1): # evaluate the energy & gradient learning model
		a=MSet("H2O_trimer_move", center_=False) # Evaluate on a water trimers
		a.ReadXYZ("H2O_trimer_move")
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "training_sample"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 15 # Train for 5 epochs in total
		PARAMS["batch_size"] =  100
		PARAMS["test_freq"] = 1 # Test for every epoch
		PARAMS["tf_prec"] = "tf.float64" # double precsion
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["NeuronType"] = "sigmoid_with_param" # choose activation function
		PARAMS["sigmoid_alpha"] = 100.0  # activation params
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0] # each layer's keep probability for dropout
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="AtomizationEnergy")
		tset = TensorMolData_BP_Direct_EandG_Release(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EandG_SymFunction")
		manager = TFMolManage("Mol_water_mini_ANI1_Sym_Direct_fc_sqdiff_BP_Direct_EandG_SymFunction_training_sample", tset,False, "fc_sqdiff_BP_Direct_EandG_SymFunction", False, False)
		total_e = []
		for m in a.mols:
			Etotal, Ebp, Ebp_atom, force = manager.EvalBPDirectEandGLinearSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"])
			print ("Unit of energy: a.u")
			print ("Etotal: %8.6f" %(Etotal))
			print ("Unit of diple: Joules/Angstrom")
			print ("force:", force)
			total_e.append(Etotal)
		np.savetxt("EanGlearning.dat", np.asarray(total_e))

	if (1): # evalate the energy, gradient and dipole learning model
		a=MSet("H2O_trimer_move", center_=False) # Evaluate on a water trimers
		a.ReadXYZ("H2O_trimer_move")
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "training_sample"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 5 # Train for 5 epochs in total
		PARAMS["batch_size"] =  100
		PARAMS["test_freq"] = 1 # Test for every epoch
		PARAMS["tf_prec"] = "tf.float64" # double precsion
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"] = 1.0
		PARAMS["NeuronType"] = "sigmoid_with_param" # choose activation function
		PARAMS["sigmoid_alpha"] = 100.0  # activation params
		PARAMS["HiddenLayers"] = [100, 100, 100]  # number of neurons in each layer
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0] # each layer's keep probability for dropout
		PARAMS["learning_rate_dipole"] = 0.0001  # learning rate for dipole learning
		PARAMS["learning_rate_energy"] = 0.00001 # learning rate for energy & grads learning
		PARAMS["SwitchEpoch"] = 2  # Train dipole for 2 epochs, then train energy & grads

		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle_Release(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager = TFMolManage("Mol_water_mini_ANI1_Sym_Direct_fc_sqdiff_BP_Direct_EE_SymFunction_training_sample", tset,False, "fc_sqdiff_BP_Direct_EE_SymFunction", False, False)

		total_e = []
		for m in a.mols:
			Etotal, Ebp, Ebp_atom ,Ecc, Evdw, mol_dipole, atom_charge, force = manager.EvalBPDirectEELinearSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
			print ("Unit of energy: a.u")
			print ("Etotal: %8.6f  Ebp: %8.6f  Ecc: %8.6f  Evdw: %8.6f" %(Etotal, Ebp, Ecc, Evdw))
			print ("Unit of diple: a.u")
			print ("Dipole: ", mol_dipole)
			print ("Unit of diple: Joules/Angstrom")
			print ("force:", force)
			total_e.append(Etotal)
		np.savetxt("EElearning.dat", np.asarray(total_e))

Train()  # Training should be finished in about an hour depends on your computer
Eval() # Evaluate the network that you trained
