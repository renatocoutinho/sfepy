name = '3_6'
v_coors = {'m0' : (-1,-1, -1),
          'm1' : ( 1,-1, -1),
          'm2' : ( 1, 1, -1),
          'm3' : (-1, 1, -1),
          'm4' : ( 0,-1,  1),
          'm5' : ( 0, 1,  1)}
v_edges = (('m0', 'm1'),
          ('m1', 'm2'),
          ('m2', 'm3'),
          ('m3', 'm0'),
          ('m4', 'm5'),
          ('m0', 'm4'),
          ('m1', 'm4'),
          ('m2', 'm5'),
          ('m3', 'm5'))
v_faces = (('m0', 'm3', 'm2', 'm1'),
          ('m0', 'm4', 'm5', 'm3'),
          ('m0', 'm1', 'm4', ''),
          ('m1', 'm2', 'm5', 'm4'),
          ('m2', 'm3', 'm5', ''))
s_coors = {'s0' : ( -1, -1),
          's1' : (  1, -1),
          's2' : (  1,  1),
          's3' : ( -1,  1)}
s_edges = {'s3' : (('s0', 's1'),
                  ('s1', 's3'),
                  ('s3', 's0')),
          's4' : (('s0', 's1'),
                  ('s1', 's2'),
                  ('s2', 's3'),
                  ('s3', 's0'))}
s_faces = {'s3' : ('s0', 's1', 's3'), 's4' : ('s0', 's1', 's2', 's3')}

interpolation = '3_6_P1'