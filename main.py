import os
import random
import requests
import time
import json
import re
import ollama



#leave start image blank to start with describe_prompt instead
start_image: str = ""
#set the number of generations to repeat one generation consists of generation stage and an image description stage this order is the same regardless of start conditions.
#actual number of images will be generations + 1 if start image is blank.
generations: int = 200

#region: comfyUi
#path to comfyUI
path_to_comfyUi: str = "/ComfyUI_windows_portable path here  "
#relative path to output from standard ComfyUI_windows_portable
output_path: str = "ComfyUI/output"
#subfolder of output relative to the comfyUI output folder to house the folders of generation chain.
subfolder_output: str = "telephone"
#custom subfolder for the generation chain leave empty for auto incrementing subfolder.
custom_subfolder: str = ""
#relative path from standard ComfyUI to final folder for output leave blank
final_output: str = ""
#file name prefix leave empty
filename_prefix: str = ""
# ComfyUI server URL
comfyUi_address: str = "http://127.0.0.1:8188"
#checkpoint model for img gen in comfyUI ensure name is in checkpoint models folder.
checkpoint: str = "crystalClearOneVs1_v10.safetensors"
#image height and width
image_height :int = 512
image_width :int = 512
#steps in the generation process
steps: int =  20
# cfg set between 0-20 lower values will result in more deviation from describe_prompt.
cfg: int = 8
#randomize seed duh
randomize_seed: bool = True
#seed for the generation, only needs to be set if randomize_seed is false
seed: int = 0
#endregion: comfyUi variables
#region llm variables
#llm model
llm_model: str = "llava-phi3"
#describe_prompt for llm when being asked to describe an image

describe_prompt: str = ("Please describe this image as if you were prompting a image generation model to generate this exact image, give NO extra details but describe the image thoroughly. Do not include any details that are not present in the image."
                   "Do NOT include conversation or dialogue, only describe the image.")
#initial describe_prompt passed to llm if there was no starting image given.
initialization_prompt: str = ("Please imagine an idea that you would like to be turned into an image, then describe that idea in as much detail as possible as if you were describing it to image generation model."
                         " Give NO extra details but describe the scene thoroughly.")
#endregion llm variables






def get_highest_subfolder(path: str):
    items = os.listdir(path)
    directories = [item for item in items if os.path.isdir(os.path.join(path, item))]
    numeric_values = []
    for dir_name in directories:
        numbers = re.findall(r'\d+', dir_name)
        if numbers:
            numeric_values.extend(map(int, numbers))
    return max(numeric_values) if numeric_values else 0
def gen_image(workflow: json,prompt: str):
    workflow["6"]["inputs"]["text"] = prompt
    workflow["3"]["inputs"]["seed"] = random.randint(-1, 2**32 - 1) if randomize_seed else seed

    response = requests.post(f"{comfyUi_address}/prompt", json={"prompt": workflow})
    prompt_id = response.json()['prompt_id']

    # wait on comfy
    while True:
        response = requests.get(f"{comfyUi_address}/history/{prompt_id}")
        data = response.json()
        if len(data) > 0 and 'outputs' in data[prompt_id]:
            break
        time.sleep(1)


    output_data = data[prompt_id]['outputs']['9']
    image_filename = output_data['images'][0]['filename']
    image_subfolder = output_data['images'][0]['subfolder']
    image_path = os.path.join(comfyUi_address, "view", image_subfolder, image_filename)

    print(f"Image saved to: {image_path}")
    return path_to_comfyUi + "/" + output_path + "/" + final_output + "/" + image_filename
def gen_image_description(image, prompt: str ,):
    filename = image.split("/")[-1]
    filename = filename.split(".")[0]
    filename = filename[:-1]
    filename = filename + "Description"
    with open(image, "rb") as f:
      data =  [{
            "role": "user",
            "content": prompt,
             "images": [f.read()],
           },]
    response = ollama.chat(model=llm_model,messages=data)

    with open (path_to_comfyUi + "/" + output_path + "/" + final_output + "/" + filename+ ".txt", "w") as f:
        f.write(response["message"]["content"])
        f.write("\n\n\n\n")
        f.write("Console:This description will be the next prompt in the series.")
    print(response["message"]["content"])
    return response["message"]["content"]
def loop(generations: int,initial_prompt: str):
    prompt = initial_prompt
    for i in range(generations):
        image = gen_image(workflow,prompt)
        prompt = gen_image_description(image,describe_prompt)

#region subfolder stuff
if not subfolder_output in os.listdir(os.path.join(path_to_comfyUi, output_path)):
    os.mkdir(os.path.join(path_to_comfyUi, output_path, subfolder_output))
if not custom_subfolder:
    final_output = f"{subfolder_output}/generationChain{get_highest_subfolder(os.path.join(path_to_comfyUi, output_path, subfolder_output)) + 1}"
    os.mkdir(os.path.join(path_to_comfyUi, output_path, final_output))

    filename_prefix = final_output + "/image"
else:
    if custom_subfolder in os.listdir(os.path.join(path_to_comfyUi, output_path, subfolder_output)):
        raise Exception("Custom subfolder already exists. Please choose a different name.")
if not final_output in os.listdir(os.path.join(path_to_comfyUi, output_path, subfolder_output)):
    print(f"{subfolder_output}/{final_output}")
#endregion subfolder stuff
#load json workflow
with open("workflow.json","r") as f:
    workflow_str = f.read()
workflow_str = re.sub(r"{{(\w+)}}", lambda m: str(globals()[m.group(1)]), workflow_str)
workflow = json.loads(workflow_str)




first_description = gen_image_description(start_image, describe_prompt) if start_image else gen_image_description(gen_image(workflow, initialization_prompt), describe_prompt)
loop(generations,first_description)
