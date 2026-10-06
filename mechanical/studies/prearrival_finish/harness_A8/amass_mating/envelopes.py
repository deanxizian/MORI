"""Rebuild study envelopes from AMASS 2025V1, without changing real hardware.

Call inside the existing read-only Blender study bootstrap. This replaces only
the temporary clearance boxes, not purchased component geometry or PCB data.
"""

def rebuild(plug, portrows, port_pins, namespace, mode):
    np=namespace['np']; manifold=namespace['manifold']; bpy=namespace['bpy']
    Matrix=namespace['Matrix']; Solid=namespace['Solid']
    assert mode in ('nominal', 'upper_with_thickness_allocation')
    size=np.array([10.2, 5.6, 17.1] if mode=='nominal' else [10.5, 5.9, 17.9])
    rows=[]
    for name,s in list(plug.items()):
        row=portrows[name]
        if row['mating']!='AMASS XT30U-F': continue
        assert abs(row['mated_height_mm']-23.1)<1e-8
        axis=np.asarray(port_pins[name]['axis'],float)
        pins=port_pins[name]['pins']; keys=sorted(pins,key=int)
        x=np.asarray(pins[keys[-1]])-np.asarray(pins[keys[0]])
        x=x-axis*(axis@x);x/=np.linalg.norm(x)
        rot=np.column_stack((x,np.cross(axis,x),axis))
        assert np.linalg.det(rot)>.999999
        old_bounds=np.r_[s.lo,s.hi]
        base=(s.lo+s.hi)/2-axis*23.1/2
        center=base+axis*size[2]/2
        m=manifold.Manifold.cube(size.tolist(),True).transform(np.c_[rot,center])
        data=m.to_mesh64(); mesh=bpy.data.meshes.new('A8_AMASS_'+mode+'_'+name)
        mesh.from_pydata(data.vert_properties[:,:3].tolist(),[],data.tri_verts.tolist());mesh.update()
        obj=s.o;obj.data=mesh;obj.matrix_world=Matrix.Identity(4)
        obj['data_status']='ASSUMED'
        obj['model_fidelity']='Dimensioned study envelope; per-field source bounds, not vendor CAD'
        bpy.context.view_layer.update();plug[name]=Solid(obj)
        rows.append({'id':name,'mode':mode,'mating_pair':['XT30UPB-M','XT30U-F'],
            'old_bounds_mm':old_bounds.tolist(),'new_bounds_mm':np.r_[plug[name].lo,plug[name].hi].tolist(),
            'base_world_mm':base.tolist(),'axis':axis.tolist(),'orientation_3x3':rot.tolist(),
            'housing_xyz_mm':size.tolist(),
            'field_evidence':{'width':'VENDOR_DOCUMENTED','height':'DERIVED_FROM_DOCUMENTED_DIMENSIONS',
                'depth':('VENDOR_DOCUMENTED_NOMINAL' if mode=='nominal' else 'ASSUMED_FEMALE_THICKNESS_MARGIN')},
            'unmodeled':['solder fillet','heat-shrink insulation','actual lead departure/bend','supplier tolerances not shown']})
    assert {r['id'] for r in rows}=={'power_J1','power_J2','power_J3','power_J4','power_J5','power_J11','power_J12'}
    return rows
