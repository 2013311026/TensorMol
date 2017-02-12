import pickle
import numpy as np
from TensorMol import *

a=MSet("gdb9_1_6_7_8")
a.Load()
mol_index_list = pickle.load(open("test_atom_index.dat", "rb"))

bond_energys = []
eles = a.BondTypes()
for i in range (0, len(a.BondTypes())):
        bond_energys.append(np.loadtxt("bond_"+str(i)+"_connectedbond.dat"))

if (0):
	index_list = [10000,20000,30000,40000,50000,60000,70000,80000,90000,100000]
	for index in index_list:
		print "mol:", index
	        for i in range (0, len(mol_index_list)):
			bond_type = eles[i]
			print "bond_type:", bond_index.keys()[bond_index.values().index(bond_type)] 
	                ele_index = mol_index_list[i]
	#		print "index:", ele_index[np.where(ele_index[:,0]==index)], 
			bond =  a.mols[index].bonds[ele_index[np.where(ele_index[:,0]==index)][:,1]]
			energies=bond_energys[i][np.where(ele_index[:,0]==index)]
			if bond.shape[0] > 0:
				for j in range (0, bond.shape[0]):
					print bond[j][1:], energies[j][1] 
			print  "\n"
	#        print a.mols[index].bonds
		a.mols[index].WriteXYZfile(fname = str(index))
		print "\n\n"

if (0):
	ele = bond_index['NN']
	ele_index = list(eles).index(ele)
	print "ele_index:", ele_index, eles
	bond_energy = bond_energys[ele_index]
	mol_index=mol_index_list[ele_index]
	badOH = 1
	for i in range (0, bond_energy.shape[0]):
		length = bond_energy[i][0]
		energy = bond_energy[i][1]
		if length < 1.2 and energy < -900:
			mol_num = mol_index[i][0]	
			bond_num = mol_index[i][1]
			print a.mols[mol_num].bonds, " bond_num", bond_num
			print "atom_index", a.mols[mol_num].bonds[bond_num]
			a.mols[mol_num].WriteXYZfile(fname = "badNN")	
			break
			

if (1):
        ele = bond_index['HC']
        ele_index = list(eles).index(ele)
        print "ele_index:", ele_index, eles
        bond_energy = bond_energys[ele_index]
        mol_index=mol_index_list[ele_index]
	maxsample = 10
	bond_range = [[1.08,1.104],[1.08, 1.11], [1.08,1.11], [1.085,1.11],[1.085, 1.11],[1.085,1.109],[1.079, 1.09],[1.08, 1.11],[1.072,1.095],[1.08, 1.095],[1.074,1.090],[1.070, 1.090], [1.10,1.13],[1.085,1.11],[1.06,1.065]]
        energy_range = [[-345, -335],[-365, -355], [-383, -373], [-398, -392], [-402, -398], [-409, -406], [-420, -415], [-426, -423], [-434, -431], [-455, -443], [-469, -462], [-478, -473], [-470, -460], [-495, -485], [-552, -547]]
	sampled_bond = [[] for k in range (0, len(bond_range))]
        bad = [0 for k in range (0, len(bond_range))]
	ord=np.random.permutation(bond_energy.shape[0])
        for i in ord:
                length = bond_energy[i][0]
                energy = bond_energy[i][1]
		for j in range (0 , len(bond_range)):
                	if bad[j] < maxsample and bond_range[j][0] < length < bond_range[j][1] and energy_range[j][0]< energy < energy_range[j][1]:
				print "found one"
				bad[j] += 1
                        	mol_num = mol_index[i][0]
                        	bond_num = mol_index[i][1]
                        	#print a.mols[mol_num].bonds, " bond_num", bond_num
				sampled_bond[j].append([a.mols[mol_num].bonds[bond_num][-2]+1, a.mols[mol_num].bonds[bond_num][-1]+1, energy, length])
				print [a.mols[mol_num].bonds[bond_num][-2]+1, a.mols[mol_num].bonds[bond_num][-1]+1, energy, length], a.mols[mol_num].bonds, bond_num, a.mols[mol_num].atoms
                        	#print "atom_index", a.mols[mol_num].bonds[bond_num], " energy", energy, "length", length
                        	a.mols[mol_num].WriteXYZfile(fpath = "./BP_mol_xyz", fname = "HC_type_"+str(j)+"_case_"+str(bad[j]))
	for i in range (0, len(bond_range)):
		print "type ",i , '\n', sampled_bond[i]	
		print "\n\n"
