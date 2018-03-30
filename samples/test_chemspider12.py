
from __future__ import absolute_import
from __future__ import print_function
from TensorMol import *
import os
os.environ["CUDA_VISIBLE_DEVICES"]=""
from TensorMol.ForceModels.ElectrostaticsTF import *
from TensorMol.MBE.NN_MBE import *


def TrainPrepare():
	if (0):
		WB97XDAtom={}
		WB97XDAtom[1]=-0.5026682866
		WB97XDAtom[6]=-37.8387398698
		WB97XDAtom[7]=-54.5806161811
		WB97XDAtom[8]=-75.0586028656
		a = MSet("chemspider12_clean")
		dic_list = pickle.load(open("./datasets/chemspider12_wb97xd_goodones.dat", "rb"))
		for mol_index, dic in enumerate(dic_list):
			atoms = []
			print ("mol_index:", mol_index)
			for atom in dic['atoms']:
				atoms.append(AtomicNumber(atom))
			atoms = np.asarray(atoms, dtype=np.uint8)
			mol = Mol(atoms, dic['xyz'])
			mol.properties['charges'] = dic['charges']
			mol.properties['dipole'] = np.asarray(dic['dipole'])
			mol.properties['quadropole'] = dic['quad']
			mol.properties['energy'] = dic['scf_energy']
			mol.properties['gradients'] = dic['gradients']
			mol.properties['atomization'] = dic['scf_energy']
			for i in range (0, mol.NAtoms()):
				mol.properties['atomization'] -= WB97XDAtom[mol.atoms[i]]
			a.mols.append(mol)
		a.mols[100].WriteXYZfile(fname="chemspider12_test")
		print(a.mols[100].properties)
		a.Save()

	if (0):
		a = MSet("chemspider12_clean")
		a.Load()
		b = MSet("chemspider12_clean_maxatom35")
		hist = np.zeros((10))
		for mol in a.mols:
			if mol.NAtoms() <= 35:
				b.mols.append(mol)
		b.Save()

	if (0):
 		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		random.shuffle(a.mols)

		b = MSet("chemspider12_clean_maxatom35_mini")
		for i in range(0, int(0.01*len(a.mols))):
			b.mols.append(a.mols[i])
		b.Save()

		c = MSet("chemspider12_clean_maxatom35_small")
		for i in range(0, int(0.05*len(a.mols))):
			c.mols.append(a.mols[i])
		c.Save()

#H2O_wbxd_1to21_with_prontonated_with_ch4.dat
	if (1):
		WB97XDAtom={}
		WB97XDAtom[1]=-0.5026682866
		WB97XDAtom[6]=-37.8387398698
		WB97XDAtom[7]=-54.5806161811
		WB97XDAtom[8]=-75.0586028656
		a = MSet("chemspider12_maxatom35_H2O_with_CH4")
		dic_list = pickle.load(open("./datasets/H2O_wbxd_1to21_with_prontonated_with_ch4.dat", "rb"))
		for mol_index, dic in enumerate(dic_list):
			atoms = []
			print ("mol_index:", mol_index)
			for atom in dic['atoms']:
				atoms.append(AtomicNumber(atom))
			atoms = np.asarray(atoms, dtype=np.uint8)
			mol = Mol(atoms, dic['xyz'])
			if mol.NAtoms() <= 35:
				mol.properties['dipole'] = np.asarray(dic['dipole'])
				mol.properties['energy'] = dic['scf_energy']
				mol.properties['gradients'] = dic['gradients']
				mol.properties['atomization'] = dic['scf_energy']
				for i in range (0, mol.NAtoms()):
					mol.properties['atomization'] -= WB97XDAtom[mol.atoms[i]]
					a.mols.append(mol)
		b = MSet("chemspider12_clean_maxatom35")
		b.Load()
		print ("nmol in water/ch4:", len(a.mols))
		print ("nmol in chemspider12:", len(b.mols))
		random.shuffle(b.mols)
		for i in range(0, len(b.mols)-len(a.mols)):
			a.mols.append(b.mols[i])
		print ("nmol in  water/ch4+chemspider12:", len(b.mols))
		a.Save()

def Train():
	if (0):
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		#random.shuffle(a.mols)
		#for i in range(150000):
		#	a.mols.pop()
		TreatedAtoms = a.AtomTypes()
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  60   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["GradScalar"] = 1.0/30.0
		PARAMS["DipoleScalar"]= 1.0
		PARAMS["NeuronType"] = "relu"
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		PARAMS["Poly_Width"] = 4.6
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["learning_rate_dipole"] = 0.0001
		#PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 1
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw")
		PARAMS['Profiling']=0
		manager.Train(1)


	if (0):
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		#random.shuffle(a.mols)
		#for i in range(150000):
		#	a.mols.pop()
		TreatedAtoms = a.AtomTypes()
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  60   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["GradScalar"] = 1.0/30.0
		PARAMS["DipoleScalar"]= 1.0
		PARAMS["NeuronType"] = "relu"
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		PARAMS["Poly_Width"] = 4.6
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["AddEcc"] = True
		PARAMS["learning_rate_dipole"] = 0.0001
		#PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 1
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update")
		PARAMS['Profiling']=0
		manager.Train(1)


	if (0):
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		#random.shuffle(a.mols)
		#for i in range(150000):
		#	a.mols.pop()
		TreatedAtoms = a.AtomTypes()

		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  60   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "relu"
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 1

		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu")
		PARAMS['Profiling']=0
		manager.Train(1)

	if (0): # Normalize+Dropout+500+usual, dropout07+sigmoid100
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "act_sigmoid100"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  50   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "sigmoid_with_param"
		PARAMS["sigmoid_alpha"] = 100.0
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 0.7]
		#PARAMS["KeepProb"] = 0.7
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 2
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout")
		PARAMS['Profiling']=0
		manager.Train(1)

	if (0): # Normalize+Dropout+500+usual, dropout07+sigmoid100+rightalpha
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "act_sigmoid100_rightalpha"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  50   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "sigmoid_with_param"
		PARAMS["sigmoid_alpha"] = 100.0
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 0.7]
		#PARAMS["KeepProb"] = 0.7
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 2
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout")
		PARAMS['Profiling']=0
		manager.Train(1)
#chemspider12_maxatom35_H2O_with_CH4

	if (1): # Normalize+Dropout+500+usual, dropout07+sigmoid100+rightalpha
		a = MSet("chemspider12_maxatom35_H2O_with_CH4")
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "act_sigmoid100_rightalpha"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  50   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "sigmoid_with_param"
		PARAMS["sigmoid_alpha"] = 100.0
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 0.7]
		#PARAMS["KeepProb"] = 0.7
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 2
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout")
		PARAMS['Profiling']=0
		manager.Train(1)

	if (0): # Normalize+Dropout+500+usual, dropout07+sigmoid100+nodropout
		a = MSet("chemspider12_clean_maxatom35")
		a.Load()
		random.shuffle(a.mols)
		TreatedAtoms = a.AtomTypes()
		PARAMS["NetNameSuffix"] = "act_sigmoid100_nodropout"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  50   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "sigmoid_with_param"
		PARAMS["sigmoid_alpha"] = 100.0
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["DSFAlpha"] = 0.18
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 1.0]
		#PARAMS["KeepProb"] = 0.7
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 2
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout")
		PARAMS['Profiling']=0
		manager.Train(1)
	if (0):
		#a = MSet("chemspider12_clean_mini")
		a = MSet("chemspider12_clean_maxatom35_small")
		a.Load()
		#random.shuffle(a.mols)
		#for i in range(150000):
		#	a.mols.pop()
		TreatedAtoms = a.AtomTypes()
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 101
		PARAMS["batch_size"] =  60   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 2
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["GradScalar"] = 1.0/30.0
		PARAMS["DipoleScalar"]= 1.0
		PARAMS["NeuronType"] = "relu"
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["AddEcc"] = False
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		PARAMS["Poly_Width"] = 4.6
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 20
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw")
		PARAMS['Profiling']=0
		manager.Train(1)

def Eval():
	if (1):
		#a=MSet("aspirin", center_=False)
		#a.ReadXYZ("aspirin")
		#a=MSet("chemspider_IR_test_mol", center_=False)
		#a.ReadXYZ("chemspider_IR_test_mol")
		a=MSet("decalin_reaction", center_=False)
		a.ReadXYZ("decalin_reaction")
		#a=MSet("IR_debug", center_=False)
		#a.ReadXYZ("IR_debug")
		TreatedAtoms = np.array([1,6,7,8], dtype=np.uint8)
		PARAMS["NetNameSuffix"] = "act_sigmoid100"
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 21
		PARAMS["batch_size"] =  50   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["EnergyScalar"] = 1.0
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "sigmoid_with_param"
		PARAMS["sigmoid_alpha"] = 100.0
		PARAMS["HiddenLayers"] = [2000, 2000, 2000]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		#PARAMS["Poly_Width"] = 4.6
		PARAMS["Elu_Width"] = 4.6  # when elu is used EECutoffOn should always equal to 0
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		#PARAMS["DSFAlpha"] = 0.18
		PARAMS["DSFAlpha"] = 0.18*BOHRPERA
		PARAMS["AddEcc"] = True
		PARAMS["KeepProb"] = [1.0, 1.0, 1.0, 0.7]
		#PARAMS["KeepProb"] = 0.7
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 2
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")  # Initialize a digester that apply descriptor for the fragme
		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("Mol_chemspider12_clean_maxatom35_ANI1_Sym_Direct_fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout_act_sigmoid100", tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_DSF_elu_Normalize_Dropout",False,False)

		m = a.mols[0]
		eq_coords = m.coords.copy()
		#print manager.EvalBPDirectEEUpdateSinglePeriodic(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
		#print manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
		#return
		#charge = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)[6]
		#bp_atom = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)[2]
		#for i in range (0, m.NAtoms()):
		#	print i+1, charge[0][i],bp_atom[0][i]

		def EnAndForce(x_, DoForce=True):
			m.coords = x_
			Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
			energy = Etotal[0]
			force = gradient[0]
			if DoForce:
				return energy, force
			else:
				return energy

		def GetEnergyForceForMol(m):
			def EnAndForce(x_, DoForce=True):
				tmpm = Mol(m.atoms,x_)
				Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
				energy = Etotal[0]
				force = gradient[0]
				if DoForce:
					return energy, force
				else:
					return energy
			return EnAndForce

		def EnForceCharge(x_):
			m.coords = x_
			Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
			energy = Etotal[0]
			force = gradient[0]
			return energy, force, atom_charge[0]

		def ChargeField(x_):
			m.coords = x_
			Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient = manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
			energy = Etotal[0]
			force = gradient[0]
			return atom_charge[0]

		def EnergyField(x_):
			return EnAndForce(x_,True)[0]

		def DipoleField(x_):
			#q = np.asarray([-0.045124, -0.077051, -0.103131, -0.086186, -0.325407, -0.181912,  0.206067, -0.339910, -0.318228, -0.345008,  0.453050,  0.299429, -0.345770,  0.269782,  0.136701,  0.118730,  0.118365,  0.119473,  0.150804,  0.149447,  0.145880])
			q = np.asarray(ChargeField(x_))
			#q = ChargeField(eq_coords)
			#dipole = Dipole(x_, q)
			#dipole = np.einsum("ax,a...", x_ , q)
			dipole = np.zeros(3)
			for i in  range(0, q.shape[0]):
				dipole += q[i]*x_[i]
			return dipole

		DFTForceField = lambda x: np.asarray([QchemDFT(Mol(m.atoms,x),basis_ = '6-31g',xc_='b3lyp', jobtype_='sp', threads=12)])[0]
		DFTDipoleField = lambda x: QchemDFT(Mol(m.atoms,x),basis_ = '6-31g',xc_='b3lyp', jobtype_='dipole', threads=12)
		#ForceField = lambda x: EnAndForce(x)[-1]
		#EnergyField = lambda x: EnAndForce(x)[0]
		EnergyForceField = lambda x: EnAndForce(x)

		PARAMS["OptMaxCycles"]=1
		Opt = GeomOptimizer(EnAndForce)
		m=Opt.Opt(a.mols[1])
		#return
		##return
 		#masses = np.array(list(map(lambda x: ATOMICMASSESAMU[x-1],m.atoms)))
		#w,v = HarmonicSpectra(DFTForceField, m.coords, m.atoms, WriteNM_=False)
		#w,v = HarmonicSpectra(DFTForceField, m.coords, m.atoms,  WriteNM_=True, Mu_ = DFTDipoleField)
		#w,v = HarmonicSpectra(EnergyField, m.coords, m.atoms, WriteNM_=True, Mu_ = DFTDipoleField)
		#w,v = HarmonicSpectra(EnergyField, m.coords, m.atoms, WriteNM_=True, Mu_ = DipoleField)
		#return


		#PARAMS["OptMaxCycles"]=200
		#Opt = GeomOptimizer(EnAndForce)
		#a.mols[0] = Opt.Opt(a.mols[0],"1")
		#a.mols[1] = Opt.Opt(a.mols[1],"2")
		#a.mols[-2], a.mols[-1] = a.mols[-2].AlignAtoms(a.mols[-1])
		PARAMS["OptMaxCycles"]=20000
		PARAMS["NebSolver"]="SD"
		PARAMS["NebNumBeads"] = 21
		PARAMS["MaxBFGS"] = 12
		PARAMS["NebK"] = 0.2
		neb = NudgedElasticBand(EnAndForce,a.mols[-2],a.mols[-1])
		Beads = neb.Opt()
		return
		##m.coords[0] = m.coords[0] + 0.1
                #PARAMS["MDThermostat"] = "Nose"
                #PARAMS["MDTemp"] = 300
                #PARAMS["MDdt"] = 0.1
                #PARAMS["RemoveInvariant"]=True
                #PARAMS["MDV0"] = None
                #PARAMS["MDMaxStep"] = 10000
                #md = VelocityVerlet(None, m, "water_trimer_nothermo",EnergyForceField)
                #md.Prop()
		##return

		##PARAMS["OptMaxCycles"]=1000
		##Opt = GeomOptimizer(EnergyForceField)
		##m=Opt.Opt(m)

		#PARAMS["MDdt"] = 0.2
		#PARAMS["RemoveInvariant"]=True
		#PARAMS["MDMaxStep"] = 2000
		#PARAMS["MDThermostat"] = "Nose"
		#PARAMS["MDV0"] = None
		#PARAMS["MDAnnealTF"] = 1.0
		#PARAMS["MDAnnealT0"] = 300.0
		#PARAMS["MDAnnealSteps"] = 1000
		#anneal = Annealer(EnergyForceField, None, m, "AnnealAspirin")
		#anneal.Prop()
		#m.coords = anneal.Minx.copy()
		#m.WriteXYZfile("./results/", "Anneal_opt_dropout_sigmoid100_10water")
		#return

		PARAMS["MDdt"] = 0.2
		PARAMS["RemoveInvariant"]=True
		PARAMS["MDMaxStep"] = 10000
		PARAMS["MDThermostat"] = "Nose"
		PARAMS["MDV0"] = None
		PARAMS["MDAnnealTF"] = 300.0
		PARAMS["MDAnnealT0"] = 0.1
		PARAMS["MDAnnealSteps"] = 10000
		anneal = Annealer(EnergyForceField, None, m, "WarmAspirin")
		anneal.Prop()
		m.coords = anneal.x.copy()
		#m.WriteXYZfile("./results/", "warm")
		PARAMS["MDThermostat"] = None
		PARAMS["MDTemp"] = 0
		PARAMS["MDdt"] = 0.1
		PARAMS["MDV0"] = None
		PARAMS["MDMaxStep"] = 40000
		md = IRTrajectory(EnergyForceField, ChargeField, m, "Aspirin_IR_300K_sigma100_wrongalpha", anneal.v)
		md.Prop()
		WriteDerDipoleCorrelationFunction(md.mu_his)
		return

#TrainPrepare()
#Train()
Eval()
