import numpy as np
import random
import os
import h5py


def rotate_translate_jitter_pc(pc, angle, x,y,z):

    """
    Rotate a point counterclockwise by a given angle around a given origin.
    The angle should be given in radians.
    """
    for p in range (pc.shape[0]):
        ox, oy, oz = [0,0,0]
        px = pc['x_cc'][p]
        py = pc['y_cc'][p]
	    
	    # Do via Matrix mutiplication istead
        qx = ox + np.cos(angle) * (px - ox) - np.sin(angle) * (py - oy) + x + (np.random.rand() * (0.02 * 2) - 0.04 )
        qy = oy + np.sin(angle) * (px - ox) + np.cos(angle) * (py - oy) + y + (np.random.rand() * (0.02 * 2) - 0.04 )
	    #qz = pz + z  + (np.random.rand() * (0.05 * 2) - 0.05 )
        
        pc['x_cc'][p] = qx
        pc['y_cc'][p] = qy
        
        #pc[p,0:2] = qx, qy, pz
	   
    return pc
    
def shuffle_pc(pc):

  idx = np.arange(len(pc))
  np.random.shuffle(idx)
  pc =pc[idx]
  
  return pc

def get_fixed_number_radar_data(radar_data,new_npoints):
  unique_frames = set(radar_data['frame'])
  new_radar_data =[]

  for frame in unique_frames:
    pc = radar_data[radar_data['frame'] == frame]
    npoints = len(pc) - new_npoints

    if ( npoints < 0):
      while  (npoints < 0) :
        # find npoints with high doopler
        k = abs(npoints)
        indices = np.argsort(pc['vr_sc'])[-k:]
        high_speed_pts = pc[indices]
        pc =  np.concatenate( (pc,high_speed_pts), axis =0)
        npoints = len(pc) - new_npoints

    if ( npoints > 0):
      # find npoints with low doopler
      k = abs(npoints)
      indices = np.argsort(pc['vr_sc'])[:k]
      pc = np.delete(pc, indices, axis=0)
    new_radar_data.append(pc)
    
    if(pc.shape[0] !=new_npoints):
        print("[ERROR] Up/Down sampling the point cloud")
        exit()

  return new_radar_data
  
class MMW(object):
    def __init__(
        self,
        root='/scratch/uceepdg/ghost_data/original/train/',
        seq_length=100,
        num_points=200,
        train=True,
    ):

        self.seq_length = seq_length
        self.num_points = num_points
        self.data = []

        log_nr = 0
        
        if not(train):


            # Original Point Cloud returns
            # (#sequences,#frames,#)
            root = root +'/test'
            
            #return files in the Folder
            h5_files = os.listdir(root)
            
            for run in h5_files:
                print("[Load]:", run)
                file_path = os.path.join(root, run)
                with h5py.File(file_path, 'r') as data: radar_data = np.copy(data['radar']) # numpy struct array
                #print("radar_data.shape", radar_data.shape) 
                
                # Interpolate or Downsample 
                new_radar_data = get_fixed_number_radar_data(radar_data,num_points)
                new_radar_data = np.array(new_radar_data)

                # Remove data we do not want
                new_data = np.zeros( (new_radar_data.shape[0],new_radar_data.shape[1],4) )
                new_data[:,:, 0] = new_radar_data['x_cc']
                new_data[:,:, 1] = new_radar_data['y_cc']
                new_data[:,:, 3] = new_radar_data['label_id']
                new_radar_data = new_data
                
                # Manipulate labels
                # Manipulate labels
                for frame in range (0,new_radar_data.shape[0]):
                    for point in range(0, new_radar_data.shape[1]):
                        if(new_radar_data[frame,point,3] ==-1): new_radar_data[frame,point,3] = 1
                        if(new_radar_data[frame,point,3] ==-2): new_radar_data[frame,point,3] = 1
                        if(new_radar_data[frame,point,3] != 1): new_radar_data[frame,point,3] = 0
                
                
                #keep adding sequence                                
                start = 0
                end = start + seq_length
                run_size = new_radar_data.shape[0]
                while end < run_size:
                    npy_data = new_radar_data[start:end, :, :]
                    self.data.append(new_radar_data)
                    start = start + seq_length
                    end = start + seq_length
                
       

            print("Validation data", np.shape(self.data) ) # (nr_sequences,) 
                      
         

    def __len__(self):
        return len(self.data)

    def __getitem__(self, nr):


        # select a seqeunce
        nr_seq = len(self.data)
        rand = nr
        log_data = self.data[rand]
        total_lenght = len(log_data)

        # print("nr frames:", total_lenght)
        start_limit = total_lenght - self.seq_length
        start = 0

        #print("[Seq] %d (of %d)  [%d - %d] (of %d)"% (rand, nr_seq, start, start + self.seq_length, total_lenght) )

        cloud_sequence = []
        cloud_sequence_color = []

        for i in range(start, start + self.seq_length):
            pc = log_data[i]

            npoints = pc.shape[0]
            # sample_idx = np.random.choice(npoints, self.num_points, replace=False)

            cloud_sequence.append(pc)

        points = np.stack(cloud_sequence, axis=0)

        return points
