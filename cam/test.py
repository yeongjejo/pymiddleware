import joblib
import numpy as np
from scipy.spatial.transform import Rotation as R

file_path = "outputs/results/demo_gongju.pkl"

data = joblib.load(file_path)

print("로드 성공")
print(type(data))

if isinstance(data, dict):
    print(data.keys())
elif isinstance(data, (list, tuple)):
    print(len(data))
    print(data[0] if len(data) > 0 else None)
else:
    print(data)


# dict_keys(['time', 'shot', 'frame_path', 'tracked_ids', 'tracked_bbox', 'tid', 'bbox', 'tracked_time', 'appe', 'loca', 'pose', 'center', 'scale', 'size', 'img_path', 'img_name', 'class_name', 'conf', 'annotations', 'smpl', 'camera', 'camera_bbox', '3d_joints', '2d_joints', 'mask', 'extra_data'])
for i in data.values():



    r = R.from_matrix(np.array(i['smpl'][0]['body_pose'], dtype=np.float64))
    root_r = R.from_matrix(np.array(i['smpl'][0]['global_orient'], dtype=np.float64))

    # scipy 기본 출력 순서: [x, y, z, w]
    quats_wxyz = r.as_quat()[:, [3, 0, 1, 2]]
    root_quats_wxyz = root_r.as_quat()[:, [3, 0, 1, 2]]


    # print(quats_wxyz)  # (N, 4)
    print(root_quats_wxyz)
    print(len(root_quats_wxyz))
    print('-----')

    #
    # print(i['smpl'][0]['global_orient'])
    # print(i['smpl'][0]['body_pose'])
    # print(i['pose'][0])
