from __future__ import absolute_import
#import memory_util
#memory_util.vlog(1)
from TensorMol import *
import os
os.environ["CUDA_VISIBLE_DEVICES"]=""
from TensorMol.ElectrostaticsTF import *
from TensorMol.NN_MBE import *
from TensorMol.TMIPIinterface import *
import random

def TestPeriodicLJVoxel():
	"""
	Tests a Simple Periodic optimization.
	Trying to find the HCP minimum for the LJ crystal.
	"""
	if (1):
		#a=MSet("H2O_cluster_meta", center_=False)
		#a.ReadXYZ("H2O_cluster_meta")
		a=MSet("water_tiny", center_=False)
		a.ReadXYZ("water_tiny")
		m = a.mols[-1]
		m.coords = m.coords - np.min(m.coords) + 0.00001

		TreatedAtoms = a.AtomTypes()
		PARAMS["learning_rate"] = 0.00001
		PARAMS["momentum"] = 0.95
		PARAMS["max_steps"] = 101
		PARAMS["batch_size"] =  150   # 40 the max min-batch size it can go without memory error for training
		PARAMS["test_freq"] = 1
		PARAMS["tf_prec"] = "tf.float64"
		PARAMS["GradScalar"] = 1.0/20.0
		PARAMS["DipoleScaler"]=1.0
		PARAMS["NeuronType"] = "relu"
		PARAMS["HiddenLayers"] = [500, 500, 500]
		PARAMS["EECutoff"] = 15.0
		PARAMS["EECutoffOn"] = 0
		#PARAMS["Erf_Width"] = 1.0
		PARAMS["Poly_Width"] = 4.6
		#PARAMS["AN1_r_Rc"] = 8.0
		#PARAMS["AN1_num_r_Rs"] = 64
		PARAMS["EECutoffOff"] = 15.0
		#PARAMS["EECutoffOff"] = 15.0
		PARAMS["learning_rate_dipole"] = 0.0001
		PARAMS["learning_rate_energy"] = 0.00001
		PARAMS["SwitchEpoch"] = 15
		d = MolDigester(TreatedAtoms, name_="ANI1_Sym_Direct", OType_="EnergyAndDipole")

		tset = TensorMolData_BP_Direct_EE_WithEle(a, d, order_=1, num_indis_=1, type_="mol",  WithGrad_ = True)
		manager=TFMolManage("Mol_H2O_wb97xd_1to21_ANI1_Sym_Direct_fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw_1",tset,False,"fc_sqdiff_BP_Direct_EE_ChargeEncode_Update_vdw",False,False)
		#print np.sum(manager.EvalBPDirectEEUpdateSinglePeriodic(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())[6])
		#print manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)

		#cellsize = 6.0
		cellsize = 9.3215
		lat = cellsize*np.eye(3)
		PF = TFPeriodicVoxelForce(15.0,lat)
		#zp, xp = PF(m.atoms,m.coords,lat)  # tessilation in TFPeriodic seems broken   
		
		#PF.tess = np.array([[0,0,0]])
		zp = np.zeros(m.NAtoms()*PF.tess.shape[0], dtype=np.int32)
		xp = np.zeros((m.NAtoms()*PF.tess.shape[0], 3))
		for i in range(0, PF.tess.shape[0]):
			zp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.atoms
			xp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.coords + cellsize*PF.tess[i]
		#print (zp.shape, xp)
		m_periodic = Mol(zp, xp)
		#output =  manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
		#output =  manager.EvalBPDirectEEUpdateSinglePeriodic(m_periodic, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
		#print ("energy:", output[0])#, " gradient:", -output[-1]/JOULEPERHARTREE)
		#print ("output[-1][0][50:60]", -output[-1][0][50:60]/JOULEPERHARTREE)
	
		#origin_coords = m_periodic.coords.copy()	
		#disp = 0.0001
		#step = 0.01
		#m.coords[:30] = m.coords[:30] + output[-1][0][:30]/JOULEPERHARTREE*step
		#m.coords[:m.NAtoms()] = m.coords[:m.NAtoms()] + output[-1]/JOULEPERHARTREE*step
		#m_periodic.coords[50][0] = m_periodic.coords[50][0] + disp
		#m_periodic.coords[:30] = origin_coords[:30] + output[-1][0][:30]/JOULEPERHARTREE*step
		#m_periodic.coords[:m.NAtoms()] = m_periodic.coords[:m.NAtoms()] + output[-1][0]/JOULEPERHARTREE*step
		##zp = np.zeros(m.NAtoms()*PF.tess.shape[0], dtype=np.int32)
		##xp = np.zeros((m.NAtoms()*PF.tess.shape[0], 3))
		##for i in range(0, PF.tess.shape[0]):
		##	zp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.atoms
		##	xp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.coords + cellsize*PF.tess[i]
		##print (zp.shape, xp)
		##m_periodic = Mol(zp, xp)
		#output1 =  manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
		#output1 =  manager.EvalBPDirectEEUpdateSinglePeriodic(m_periodic, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
		#print ("energy:", output1[0])#, " gradient:", -output1[-1]/JOULEPERHARTREE)
		#print ("num gradient:", (output1[0]-output[0])/disp)
		#print ("gradient rms:", np.sum(np.square(output[-1][0]/JOULEPERHARTREE-output1[-1][0]/JOULEPERHARTREE))**0.5)
		#print ("num bp gradient:", (output1[1]-output[1])/disp)
		#print ("num cc gradient:", (output1[3]-output[3])/disp)
		##output =  manager.EvalBPDirectEEUpdateSingle(m, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], True)
		#print ("energy:", output[0], " gradient:", -output[-1]/JOULEPERHARTREE)

		#step = 0.0001
		#print ("before move:", m_periodic.coords[50])
		#m_periodic.coords[50] = coords1[50] + output1[-1][0][50]/JOULEPERHARTREE*step
		##print ("diff from 1:", np.equal(coords1[:m.NAtoms()], m_periodic.coords[:m.NAtoms()]))
		#print ("after move:", m_periodic.coords[50])
		##m_periodic.coords[50] = m_periodic.coords[50] + output1[-1][0][50]/JOULEPERHARTREE*step
		#np.set_printoptions(threshold=np.nan)
		#output2 =  manager.EvalBPDirectEEUpdateSinglePeriodic(m_periodic, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
		##print ("diff !:", coords1 - m_periodic.coords)
		#print ("after evaluation:", m_periodic.coords[50])
		#print ("energy:", output2[0])#, " gradient:", -output2[-1]/JOULEPERHARTREE)
		#print ("output2[-1][0][50:60]", -output2[-1][0][50:60]/JOULEPERHARTREE)
		#print ("output2[0]-output1[0]",output2[:4], output1[:4])
		#print ("charge diff:", output2[2] - output1[2])
		#print ("num gradient:", (output2[0]-output1[0])/disp)
		#return


		def EnAndForce(x_):
			x_ = np.mod(x_, cellsize)
			xp = np.zeros((m.NAtoms()*PF.tess.shape[0], 3))
			for i in range(0, PF.tess.shape[0]):
				xp[i*m.NAtoms():(i+1)*m.NAtoms()] = x_ + cellsize*PF.tess[i]
			m_periodic.coords = xp
			m_periodic.coords[:m.NAtoms()] = x_
			Etotal, gradient  = manager.EvalBPDirectEEUpdateSinglePeriodic(m_periodic, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
			#Etotal, Ebp, Ebp_atom, Ecc, Evdw, mol_dipole, atom_charge, gradient  = manager.EvalBPDirectEEUpdateSinglePeriodic(m_periodic, PARAMS["AN1_r_Rc"], PARAMS["AN1_a_Rc"], PARAMS["EECutoffOff"], m.NAtoms())
			energy = Etotal[0]
			force = gradient[0]
			print ("energy:", energy)
			return energy, force
		
		ForceField = lambda x: EnAndForce(x)[-1]
		EnergyField = lambda x: EnAndForce(x)[0]
		EnergyForceField = lambda x: EnAndForce(x)

		#EnergyForceField(m.coords)
		#return
		#PARAMS["OptMaxCycles"]=200
		#Opt = GeomOptimizer(EnergyForceField)
		#m=Opt.Opt(m)
		#return

		#PARAMS["MDdt"] = 0.2
		#PARAMS["RemoveInvariant"]=True
		#PARAMS["MDMaxStep"] = 2000
		#PARAMS["MDThermostat"] = "Nose"
		#PARAMS["MDV0"] = None
		#PARAMS["MDAnnealTF"] = 1.0
		#PARAMS["MDAnnealT0"] = 300.0
		#PARAMS["MDAnnealSteps"] = 2000	
		#anneal = Annealer(EnergyForceField, None, m, "Anneal")
		#anneal.Prop()
		#m.coords = anneal.Minx.copy()

                PARAMS["MDThermostat"] = "Nose"
                PARAMS["MDTemp"] = 200
                PARAMS["MDdt"] = 0.1
                PARAMS["RemoveInvariant"]=True
                PARAMS["MDV0"] = None
                PARAMS["MDMaxStep"] = 10000
                md = VelocityVerlet(None, m, "water_peri_10cut",EnergyForceField)
                md.Prop()
		return
	if (0):
		a=MSet("water_tiny", center_=False)
		a.ReadXYZ("water_tiny")
		m = a.mols[-1]
		m.coords = m.coords - np.min(m.coords)
		print("Original coords:", m.coords)
		# Generate a Periodic Force field.
		cellsize = 9.3215
		lat = cellsize*np.eye(3)
		PF = TFPeriodicVoxelForce(15.0,lat)
		#zp, xp = PF(m.atoms,m.coords,lat)  # tessilation in TFPeriodic seems broken   
		
		zp = np.zeros(m.NAtoms()*PF.tess.shape[0], dtype=np.int32)
		xp = np.zeros((m.NAtoms()*PF.tess.shape[0], 3))
		for i in range(0, PF.tess.shape[0]):
			zp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.atoms
			xp[i*m.NAtoms():(i+1)*m.NAtoms()] = m.coords + cellsize*PF.tess[i]
		

		#print (zp, xp)
		t0 = time.time()
		NL = NeighborListSetWithImages(xp.reshape((1,-1,3)), np.array([zp.shape[0]]), np.array([m.NAtoms()]), True, True, zp.reshape((1,-1)), sort_=True)
		rad_p_ele, ang_t_elep, mil_j, mil_jk = NL.buildPairsAndTriplesWithEleIndexPeriodic(4.6, 3.1, np.array([1,8]), np.array([[1,1],[1,8],[8,8]]))
		print ("time cost:", time.time() - t0)
		NLEE = NeighborListSetWithImages(xp.reshape((1,-1,3)), np.array([zp.shape[0]]), np.array([m.NAtoms()]), False, False,  None)
		rad_eep = NLEE.buildPairs(15.0)
		print ("time cost:", time.time() - t0)
		print (mil_j[:50], mil_jk[:50])
		print (rad_p_ele.shape, rad_eep.shape,  ang_t_elep.shape)
		return
		print (ang_t_elep)
		count = 0
		for i in range (0, rad_p_ele.shape[0]):
			if rad_p_ele[i][1] == 0:
				#print (ang_t_elep[i])
				count += 1
		print ("count", count)
		mp = Mol(zp, xp)


		mp.WriteXYZfile(fname="H2O_peri_tiny")
		cutoff = 4.6

		mostatom=[]
		mostatomele=[]
		for i in range (0, m.NAtoms()):
			around = 0
			for j in range (0, mp.NAtoms()):
				dist = np.sum(np.square(m.coords[i] - mp.coords[j]))**0.5
				if i!=j and  dist <  cutoff:
					around += 1
					if i == 7:
						mostatom.append(mp.coords[j])
						mostatomele.append(mp.atoms[j])
						print (j, mp.coords[j])
			print (around)
		mostatom = np.asarray(mostatom)
		mostatomele =  np.asarray(mostatomele, dtype=np.int32)
		most_mol = Mol(mostatomele, mostatom)
		most_mol.WriteXYZfile(fname="H2O_most")
			#for j in range(0, rad_p_ele.shape[0]):
			#	print (np.sum(np.square(m.coords[i] - mp.coords[int(rad_p_ele[j][1])]))**0.5)
		return

TestPeriodicLJVoxel()
