import cv2
# from hmr2.configs import CACHE_DIR_4DHUMANS

# def download_models(folder=CACHE_DIR_4DHUMANS):
#     """Download checkpoints and files for running inference.
#     """
#     import os
#     os.makedirs(folder, exist_ok=True)
#     download_files = {
#         "hmr2_data.tar.gz"      : ["https://www.cs.utexas.edu/~pavlakos/4dhumans/hmr2_data.tar.gz", folder],
#     }
#
#     for file_name, url in download_files.items():
#         output_path = os.path.join(url[1], file_name)
#         if not os.path.exists(output_path):
#             print("Downloading file: " + file_name)
#             # output = gdown.cached_download(url[0], output_path, fuzzy=True)
#             output = cache_url(url[0], output_path)
#             assert os.path.exists(output_path), f"{output} does not exist"
#
#             # if ends with tar.gz, tar -xzf
#             if file_name.endswith(".tar.gz"):
#                 print("Extracting file: " + file_name)
#                 os.system("tar -xvf " + output_path + " -C " + url[1])



cap = cv2.VideoCapture(0)  # 0 = 기본 웹캠

while True:
    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC 누르면 종료
        break

cap.release()
cv2.destroyAllWindows()