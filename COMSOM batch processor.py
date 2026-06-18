import copy
import datetime
import logging
import math
import os
import re
import sys
import time

import mph
from mph import Node

from open_file import open_file
from pathlib import Path
import json
import hashlib

CONFIG_FILE = __file__.replace('.py', '.json')
VERSION = "6.3"

class Variant(dict):
    def __init__(self, parent=None, auto_hash = False, **kwargs):
        super().__init__(copy.deepcopy(parent), **kwargs)
        self.old_hash = None
        self.model = None
        self.auto_hash = False
        self["version"] = VERSION
        self['errors'] = self.get('errors', [])
        self['warnings'] = self.get('errors', [])
        self['digest'] = self.get('digest', [])
        self['parameters'] = self.get('parameters', {})
        self['imports'] = self.get('imports', [])
        self['nodes'] = self.get('nodes', [])
        self['mph'] = self.get('mph', '')
        self['data_file_prefix'] = self.get('data_file_prefix', '')
        self.dts()
        self.hash()
        self.auto_hash = auto_hash

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.auto_hash and key != 'hash':
            self.hash()

    def hash(self):
        old_hash = self.get('hash' , '')
        self['hash'] = ''
        _hash = f"{hash(str(self)):>20d}"
        self['hash'] = _hash
        if _hash != old_hash:
            self.old_hash = old_hash
        return _hash

    def dts(self, store=True):
        dts = datetime.datetime.today().strftime("%Y-%m-%d %H-%M-%S")
        if store:
            self["dts"] = dts
        return dts

    def add_error(self, errstr):
        self["errors"].append(str(errstr))

    def add_warning(self, errstr):
        self["warnings"].append(str(errstr))

    def add_digest(self, errstr):
        self["digest"].append(str(errstr))


def clean_filename(filename):
    # Regex matches characters that are illegal across major OS (Windows, Mac, Linux)
    illegal_chars = r"[<>:'/\\|?*]"
    return re.sub(illegal_chars, "", filename)

def dts():
    return datetime.datetime.today().strftime("%Y-%m-%d %H-%M-%S")

def print_except_info(prefix="Exception:"):
    text = except_info(prefix=prefix)
    print(text)
    return text

def except_info(prefix="Exception:"):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if "Java Virtual Machine is not running" in str(exc_value):
        LOGGER.error("Java Virtual Machine is not running", exc_info=True)
        print('Critical ERROR, program exit')
        exit(-123)
    return f"{prefix} {exc_type} {exc_value}"

# Expansion ****************

def expand_variants_parameters(variants):
    print("")
    print("Expanding variant parameters")
    variants_expanded = []
    for variant in variants:
        var1 = Variant(variant)
        parameters = var1.get("parameters", [])
        if isinstance(parameters, dict):
            var1.hash()
            variants_expanded.append(var1)
            print("Variant #", var1["hash"], "added for parameters #", hash(str(parameters)))
            continue
        for one in parameters:
            var2 = Variant(var1)
            var2["parameters"] = one
            var2.hash()
            variants_expanded.append(var2)
            print("Variant #", var2["hash"], "added for parameters #", hash(str(one)))
    return variants_expanded

def expand_inherited_parameters(variants):
    print("")
    print("Expanding inherited parameters")
    variants_expanded = []
    for variant in variants:
        var2 = Variant(variant)
        inherited = var2.get("inherited", [])
        if len(inherited) == 0:
            variants_expanded.append(var2)
            print(f"Variant # {var2["hash"]} appended - no inheritance")
            continue
        imports = var2.get("imports", [])
        if len(imports) == 0:
            variants_expanded.append(var2)
            print(f"Variant # {var2["hash"]} appended - no imports")
            continue
        if inherited[0].get("parameters", [1])[0] == "*":
            inherited = [{"parameters": ["*"]}]
        for inh in inherited:
            inh_file = inh.get("file", None)
            inh_params = inh.get("parameters", [])
            if len(inh_params) == 0:
                continue
            for imp in imports:
                path = imp.get("path", "")
                import_file = imp.get("file", None)
                if inh_file is None or inh_file == import_file:
                    data_file = Path(path).joinpath(import_file)
                    with open(data_file, "r") as file:
                        for line in file:
                            if line.startswith("% Parameters: "):
                                line = line.replace("% Parameters:", "")
                                line = line.replace("'", '"')
                                contents = json.loads(line)
                                for element in contents:
                                    if element in inh_params or inh_params[0] == "*":
                                        if element in var2["parameters"]:
                                            msg = f"'{element}' inheritance rejected, stays '{var2["parameters"][element]}'"
                                            print(f"# {var2["hash"]} {msg}")
                                            var2.add_warning(msg)
                                        else:
                                            var2["parameters"][element] = contents[element]
                                            print(f"# {var2["hash"]} '{element}' = '{contents[element]}' inherited from '{data_file}'")
                                            var2["digest"].append(f"'{element}' = '{contents[element]}' inherited from '{data_file}'")
                                break
        tmp = var2['parameters'].pop("_", None)
        if tmp:
            var2['parameters']["_"] = tmp
        variants_expanded.append(var2)
        print(f"Variant # {var2["hash"]} appended")
    return variants_expanded

def expand_variants_imports(variants:list, recursion=False):
    if not recursion:
        print("")
        print("Expanding variant imports")
    variants_expanded = []
    expanded = False
    for variant in variants:
        var2 = Variant(variant)
        imports = var2.get("imports", [])
        if len(imports) == 0:
            var2.hash()
            variants_expanded.append(var2)
            if not recursion:
                print(f'Variant # {var2["hash"]} added - no imports')
            continue

        for imp in imports:
            _path = imp.get("path", '')
            i_path = Path(_path)
            if i_path.exists() and i_path.is_dir():
                # print(f"Import path is set to '{i_path}'")
                imp["path"] = str(i_path)
            else:
                print(f'Import path "{i_path}" does not exist')
                continue
            import_file = imp.get("file", None)
            if "*" in import_file or "?" in import_file:
                files = list(i_path.glob(import_file))
            else:
                files = [Path.joinpath(i_path, import_file)]
            n = 0
            for file in files:
                if "parameters" not in file.name:
                    imp["file"] = file.name
                    var1 = Variant(var2)
                    var1.hash()
                    variants_expanded.append(var1)
                    if len(files) > 1:
                        print(f'Variant # {var1["hash"]} for import from "{file.name}" added')
                    n += 1
            if n == 0:
                print(f"Variant expansion ERROR: No files found for '{import_file}' in '{IMPORT_PATH}'")
                variant.add_warning(f"Variant expansion ERROR: No files found for '{import_file}' in '{IMPORT_PATH}'")
            elif n > 1:
                expanded = True
                if not recursion:
                    print(f"Total {n} variants expanded from '{import_file}'")
    if not expanded:
        return variants_expanded
    # print("Entering recursion")
    variants_expanded = expand_variants_imports(variants_expanded, recursion=True)
    return variants_expanded


# Processing ****************

def process_parameters(variant:Variant):
    prop_str = ""
    try:
        params = variant.get("parameters", {})
        model_parameters = variant.model.parameters()
        # evaluated = MODEL.parameters(evaluate=True)
        for key, value in params.items():
            try:
                if key.startswith("_"):
                    for name, unit in value.items():
                        v = adjust_units(variant.model, name, unit)
                        print(f"# {variant['hash']} '{name}' -> '{v}[{unit}]'")
                        if unit == "1" or unit == "None":
                            unit = ""
                        tmp = f"_{name}_{v:g}{unit}"
                        if len(prop_str) + len(tmp) < 26:
                            prop_str += tmp
                    continue
                if key not in model_parameters:
                    print(f"# {variant['hash']} parameter '{key}' is absent in the model")
                    # variant["errors"].append(f"WARNING: Parameter '{key}' is absent in the MODEL")
                variant.model.parameter(key, value)
                print(f"# {variant['hash']} '{key}' = '{value}'")
            except:
                variant.add_error(print_except_info(f'Parameter "{key}" ERROR'))
        check_problems(variant, "parameters")
    except:
        variant.add_error(print_except_info("Parameters processing ERROR"))
        LOGGER.error("Parameters processing ERROR", exc_info=True)
    variant.add_digest(f"File name header: '{prop_str}'")
    variant.add_digest(f"Parameters: {evaluate_parameters(MODEL)}")
    return prop_str

def find_node_by_tag(node, tag, root=None):
    if root is None:
        root = node.parent()
    children = root.children()
    for nd in children:
        if nd.tag() == tag:
            return nd
    raise ValueError(f"Tag {tag} not found in {node}")

def process_particles(variant:Variant):
    # check particles type
    particles = variant.get("particles", [])
    if isinstance(particles, dict):
        particles = [particles]
    for particle in particles:
        node_name = particle.get("node", "")
        if not node_name:
            return
        value = particle.get("value", "")
        try:
            node = (variant.model / "physics/Charged Particle Tracing") / node_name
            tag = node.property("ReleasedParticleProperties")
            nd = find_node_by_tag(node, tag)
            if value not in nd.name():
                variant.add_error(f"Particle type {value} mismatch for '{node_name}' {nd.name}")
                return
            print(f"# {variant['hash']} Particles '{value}' for node '{node_name}' confirmed")
        except:
            variant.add_error(print_except_info("Particles type ERROR"))
            LOGGER.error("Particles type ERROR", exc_info=True)

def process_imports(variant:Variant):
    global IMPORT_PATH
    impts = variant.get("imports", [])
    if isinstance(impts, dict):
        impts = [impts]
    for impt in impts:
        try:
            path = impt.get("path", None)
            if path:
                IMPORT_PATH = Path(path)
                print(f"# {variant['hash']} Import path set to '{IMPORT_PATH}'")
            file = impt.get("file", None)
            if file:
                data_file = Path.joinpath(IMPORT_PATH, file)
                node = variant.model/impt.get("node", "")
                print(f"# {variant['hash']} Import to '{node}' from '{data_file}'...")
                node.java.discardData()
                node.property("Filename", data_file)
                node.java.importData()
                variant.add_digest(f"Imported to '{node}' from '{data_file}'")
        except:
            variant.add_error(print_except_info("Imports ERROR"))
            LOGGER.error("Imports ERROR", exc_info=True)

def process_node_toggless(variant:Variant):
    nodes = variant.get("nodes", [])
    if isinstance(nodes, dict):
        nodes = [nodes]
    for nd in nodes:
        try:
            node = nd.get("node", None)
            if not node:
                continue
            value = nd.get("value", "on")
            (variant.model / node).toggle(action=value)
            print(f"# {variant['hash']} Switching '{node}' to '{value}'")
            variant["digest"].append(f"Switched '{node}' to '{value}'")
        except:
            variant.add_error(print_except_info("Node switch ERROR"))
            LOGGER.error("Node switch ERROR", exc_info=True)

def process_exports(variant:Variant):
    model = variant.model
    file_name_prefix = variant["data_file_prefix"]
    exports = variant.get("exports", [])
    if isinstance(exports, dict):
        exports = [exports]
    for export in exports:
        try:
            node = export.get("node", None)
            if not node:
                continue
            value = export.get("value", "")
            if "." not in value:
                value = "." + value
            file = f"{file_name_prefix}_{variant["hash"]}{value}"
            model.export(node, file)
            print(f"# {variant['hash']} Export '{node}' to '{file}'")
            if file.endswith("txt"):
                parameters = MODEL.parameters()
                parameters_evaluated = evaluate_parameters(MODEL)
                with open(file, "a+") as fl:
                    fl.write(f"% Parameters:           {parameters}\n")
                    fl.write(f"% Parameters_evaluated: {parameters_evaluated}\n")
                    fl.write(f"% Variant: {variant}\n")
        except:
            variant.add_error(print_except_info("Export ERROR"))

def process_evaluates(variant:Variant):
    result = ""
    evs = variant.get("evaluates", [])
    if isinstance(evs, dict):
        evs = [evs]
    for ev in evs:
        try:
            expr = ev.get("expression", "")
            unit = ev.get("units", None)
            args = ev.get("args", ())
            if not expr:
                continue
            if not unit:
                unit = None
            ev["value"] = float(variant.model.evaluate(expr, unit, *args))
            print(f"# {variant['hash']} Evaluated: '{ev["expression"]}' = {ev["value"]}[{ev["units"]}]")
            if "pref" in ev:
                tmp = f"_{ev['pref']}_{ev['value']:g}{unit}"
                if len(result) + len(tmp) < 26:
                    result += tmp
        except:
            variant.add_error(print_except_info("Evaluate ERROR"))
            LOGGER.error("Evaluate ERROR", exc_info=True)
    return result

def process_solves(variant:Variant):
    slvs = variant.get("solves", [])
    for slv in slvs:
        try:
            if not slv:
                continue
            print(f"# {variant['hash']} Solving '{slv}' ...")
            variant.model.solve(slv)
            problems = (variant.model / "studies" / slv).problems()
            if problems:
                print(f"# {variant['hash']} Solving problems: '{problems}'")
                variant.add_error(f"Solving problems: '{problems}'")
        except:
            variant.add_error(print_except_info("Solves ERROR"))

def process_node_properties(variant:Variant):
    nodes = variant.get("node_properties", [])
    if isinstance(nodes, dict):
        nodes = [nodes]
    for nd in nodes:
        node_name = nd.get("node", None)
        if not node_name:
            continue
        name = nd.get("name", "")
        if not name:
            continue
        value = nd.get("value", None)
        try:
            node = variant.model / node_name
            pattern = nd.get("regex", "")
            parent = node.parent()
            nodes1 = []
            if pattern:
                brothers = parent.children()
                for brother in brothers:
                    bn = brother.name()
                    if re.match(pattern, bn):
                        nodes1.append(brother)
            else:
                nodes1 = [node]
            if not nodes1:
                continue
            for _node in nodes1:
                # last_value = _node.property(name)
                if value is None:
                    result = _node.property(name)
                else:
                    result = _node.property(name, value=value)
                    # result = _.property(name)
                nd["result"] = result
                print(f"# {variant['hash']} '{name}' for '{_node}' changed to '{value}'")
                variant.add_digest(f"'{name}' for '{_node}' changed to '{value}'")
            check_problems(variant, parent)
        except:
            variant.add_error(print_except_info(f"Node {node_name} ERROR"))

def exec_model_actions(variant:Variant):
    actions = variant.get("actions", [])
    for action in actions:
        name = action.get("action", None)
        if not name:
            continue
        value = action.get("value", None)
        try:
            if name == "clear":
                print(f"# {variant['hash']} Clear model")
                variant.model.clear()
                continue
            if name == "save":
                print(f"# {variant['hash']} Saving to '{value}'")
                if value:
                    variant.model.save(value)
                else:
                    variant.model.save()
                continue
            if name == "raw":
                print(f"# {variant['hash']} Executing '{value}'")
                exec(value)
                variant.add_digest(f"Executed '{value}'")
        except:
            variant.add_error(print_except_info(f"Action {name} ERROR"))

def evaluate_parameters(model, tol=0):
    parameters = model.parameters(evaluate=True)
    for param in parameters:
        unit = model.java.param().evaluateUnit(param)
        val = adjust_units(model, param, unit)
        if tol > 0:
            parameters[param] = f"{val:.{tol}g} [{unit}]"
        else:
            parameters[param] = f"{val:g} [{unit}]"
    return parameters

def round_base10_mantissa(x, precision=0):
    if x == 0:
        return 0.0
    if precision <= 0:
        return x

    # Get the base-10 exponent
    exponent = math.floor(math.log10(abs(x)))

    # Isolate the base-10 mantissa (between 1.0 and 10.0)
    mantissa = x / (10 ** exponent)

    # Round the mantissa
    rounded_mantissa = round(mantissa, precision)

    # Reconstruct the value
    return rounded_mantissa * (10 ** exponent)

def split_units(model):
    param_raw = model.parameters()
    result = {}
    for key in param_raw:
        value = param_raw[key]
        unit = ""
        if "[" in value:
            unit = value.split("[")[1].split("]")[0].strip()
        result[key] = unit
    return result

def adjust_units(model:mph.Model, param:str, unit:str = "1") -> float:
    try:
        v = float(model.parameter(param, evaluate=True))
        u = model.java.param().evaluateUnit(param)
        if u != unit:
            model.parameter("k_", f"1[{unit}]/1[{u}]")
            k = float(model.parameter("k_", evaluate=True))
            model.java.param().remove("k_")
        else:
            k = 1.0
        return v / k
    except:
        print_except_info("Error adjusting units")
        return float('nan')

def check_problems(variant: Variant, node: str|Node = ''):
    try:
        if isinstance(node, str):
            node = variant.model / node
        problems = node.problems()
        if problems:
            print(f"# {variant['hash']} '{node}' problems: '{problems}'")
            variant.add_error(f"'{node}' problems: '{problems}'")
    except:
        print_except_info("Error node problems check")
        LOGGER.error("Error node problems check", exc_info=True)


def change_file(variant):
    global MPH_FILE_PREFIX, MODEL, CLIENT
    file_path = ''
    try:
        if "file" in variant:
            file_path = variant["file"]
            pfp = Path(file_path)
            if pfp.exists() and pfp.is_file():
                # mph_file_dir = Path(MPH_FILE_PATH).parent
                # os.chdir(mph_file_dir)
                # print(f"Current dir is set to: '{os.getcwd()}'")
                print(f"{dts()} Loading '{file_path}' ...")
                CLIENT.remove(MODEL)
                MODEL = CLIENT.load(file_path)
                print(f"COMSOL file changed to '{file_path}'")

                variant["mph"] = file_path
                variant.model = MODEL

                parameters = MODEL.parameters()
                print("Parameters:", parameters)
                parameters_evaluated = evaluate_parameters(MODEL)
                print("Parameters Evaluated: ", parameters_evaluated)

                variant["data_file_prefix"] = pfp.name[:6]
            else:
                print(f"File '{file_path}' does not exist")
    except:
        print_except_info("Error loading mph file")
        LOGGER.error(f"Error loading file: '{file_path}'")

def read_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.loads(file.read())
        return config
    except:
        print_except_info("Config file read error")
        LOGGER.error('config save error', exc_info=True)
        return {}

def write_config(config):
    try:
        with open(CONFIG_FILE, "w") as file:
            file.write(json.dumps(config, indent=4))
    except:
        print_except_info("Config file write error")
        LOGGER.error('config save error', exc_info=True)


t00 = time.time()

if len(sys.argv) > 1:
    CONFIG_FILE = sys.argv[1]
CONFIG = read_config()

# configure logging
LOG_FORMAT_STRING = "%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s"
if "LOG_FORMAT_STRING" in CONFIG:
    LOG_FORMAT_STRING = CONFIG["LOG_FORMAT_STRING"]
CONFIG["LOG_FORMAT_STRING"] = LOG_FORMAT_STRING

LOGGER = logging.getLogger()
log_formatter = logging.Formatter(LOG_FORMAT_STRING, datefmt="%H:%M:%S")
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
LOGGER.addHandler(console_handler)
log_level = CONFIG.get("log_level", "INFO")
CONFIG["log_level"] = log_level
LOGGER.setLevel(log_level)

print("")
print(dts(), "COMSOL batch processor Version", VERSION, "started")
print("")

# select COMSOL file
MPH_FILE_DIR = CONFIG.get("MPH_FILE_DIR", "e:/COMSOL/TRT/Beam_Transport/2026/Geometry V1")
CONFIG["MPH_FILE_DIR"] = str(MPH_FILE_DIR)
MPH_FILE_PATH = open_file(initialdir=MPH_FILE_DIR, filetypes=[("COMSOL Files", "*.mph")])
CONFIG["MPH_FILE_PATH"] = str(MPH_FILE_PATH)
if not MPH_FILE_PATH:
    exit(0)
print(f"Selected  COMSOL file: '{MPH_FILE_PATH}'")
MPH_FILE_DIR = Path(MPH_FILE_PATH).parent
CONFIG["MPH_FILE_DIR"] = str(MPH_FILE_DIR)
os.chdir(MPH_FILE_DIR)
print(f"Current dir set to '{os.getcwd()}'")
MPH_FILE_PREFIX = Path(MPH_FILE_PATH).name.replace("[", "").replace("]", "")[:6]

# select variants file
VARIANTS_FILE_PATH = open_file(initialdir=MPH_FILE_DIR,
                               initialfile="variants.json",
                               filetypes=[("Json Files", ".json")])
if not VARIANTS_FILE_PATH:
    exit(0)
VARIANTS_FILE_DIR = Path(VARIANTS_FILE_PATH).parent
CONFIG["VARIANTS_FILE_DIR"] = str(VARIANTS_FILE_DIR)
CONFIG["VARIANTS_FILE_PATH"] = str(VARIANTS_FILE_PATH)
print(dts(), f"Selected variants file: '{Path(VARIANTS_FILE_PATH)}'")
with open(VARIANTS_FILE_PATH, "r") as file:
    variants = json.loads(file.read())

IMPORT_PATH = VARIANTS_FILE_DIR

# expand variants file
variants_expanded_parameters = expand_variants_parameters(variants)
print("Total", len(variants_expanded_parameters), "variants after parameters expanded")
variants_expanded_imports = expand_variants_imports(variants_expanded_parameters)
print("Total", len(variants_expanded_imports), "variants after imports expanded")
variants_expanded = expand_inherited_parameters(variants_expanded_imports)
print("")
N = len(variants_expanded)
print(f'Total {N} variants will be processed')
if N <= 0:
    print('No variants to process, exiting')
    exit(0)

write_config(CONFIG)

print("")
print(dts(), "Starting COMSOL mph wrapper ...")
CLIENT = mph.start()

print(dts(), f"Loading '{MPH_FILE_PATH}' ...")
MODEL = CLIENT.load(MPH_FILE_PATH)

parameters = MODEL.parameters()
print("Parameters:", parameters)
parameters_evaluated = evaluate_parameters(MODEL)
print("Parameters Evaluated: ", parameters_evaluated)

print("")
print(dts(), "Processing variants ...")
processed_variants = []
nv = 1
for variant in variants_expanded:
    t0 = time.time()
    dt = [0.0]*8

    variant["mph"] = MPH_FILE_PATH
    variant.model = MODEL
    variant["data_file_prefix"] = MPH_FILE_PREFIX

    print("")
    print(f"Variant {nv} of {N}")
    nv += 1
    print("Variant start:", dts())
    variant.hash()
    if variant.old_hash != variant["hash"]:
        print(f"Variant # {variant['hash']} rehash from # {variant.old_hash}")
    else:
        print("Variant hash #", variant['hash'])

    # export_file_name_prefix = f"{MPH_FILE_PREFIX}"
    try:
        change_file(variant)

        t1 = time.time()
        process_node_toggless(variant)
        dt[0] = time.time() - t1

        t1 = time.time()
        process_node_properties(variant)
        dt[1] = time.time() - t1

        t1 = time.time()
        process_particles(variant)
        dt[2] = time.time() - t1
        # export_file_name_prefix = f"{MPH_FILE_PREFIX}_{variant.get("particles", [{"value": 'X'}])[0]["value"][0]}"
        variant["data_file_prefix"] = f"{MPH_FILE_PREFIX}_{variant.get("particles", [{"value": 'X'}])[0]["value"][0]}"

        t1 = time.time()
        parameters_string = process_parameters(variant)
        dt[3] = time.time() - t1
        temp = parameters_string.replace("[", "").replace("]", "")[:26]
        # export_file_name_prefix += parameters_string
        variant["data_file_prefix"] += parameters_string

        t1 = time.time()
        process_imports(variant)
        dt[4] = time.time() - t1

        t1 = time.time()
        process_solves(variant)
        dt[5] = time.time() - t1

        t1 = time.time()
        evaluated_string = process_evaluates(variant)
        dt[6] = time.time() - t1
        # export_file_name_prefix += evaluated_string
        variant["data_file_prefix"] += evaluated_string
        print(f"# {variant['hash']} Export file names prefix: '{variant["data_file_prefix"]}'")

        t1 = time.time()
        process_exports(variant)
        dt[7] = time.time() - t1

        exec_model_actions(variant)
    except SystemExit:
        break
    except:
        variant.add_error(print_except_info("Variant processing ERROR"))
        LOGGER.error("Variant processing ERROR", exc_info=True)

        errors = variant.get("errors", None)
        if errors:
            print("")
            print("*** ERRORS ***")
            for error in errors:
                print(f"# {variant['hash']} {error}")

    delta_t = time.time() - t0
    variant["dts"] = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    print(f"# {variant['hash']} finish: {variant["dts"]}")
    print("Total variant time:", int(delta_t), "seconds")
    idt = [int(i) for i in dt]
    print(f"Particles: {idt[0]}, Node_toggle: {idt[1]}, Node_prop: {idt[2]}, Parameters: {idt[3]}, Imports: {idt[4]}, Solves: {idt[5]}, Evaluates: {idt[6]}, Exports: {idt[7]}")
    processed_variants.append([variant["hash"], variant["dts"], variant["digest"],
                               f"{variant["data_file_prefix"]}_{variant["hash"]}"])
    # save variant to json
    json_file_name = f"variant {variant["hash"]}.json"
    with open(json_file_name, "w") as file:
        file.write(json.dumps(variant, indent=4))
        print(f"Variant saved to '{json_file_name}'")

    # save processed_variants to json
    json_file_name = f"current_processed_variants.json"
    with open(json_file_name, "w") as file:
        file.write(json.dumps(processed_variants, indent=4))
        # print(f"List of processed variants saved to '{json_file_name}'")

# save processed_variants to json
json_file_name = f"{dts().replace(":", "-")} processed_variants.json"
with open(json_file_name, "w") as file:
    file.write(json.dumps(processed_variants, indent=4))
    print(f"List of processed variants saved to '{json_file_name}'")

# Path("current_processed_variants.json").unlink(missing_ok=True)
try:
    os.remove("current_processed_variants.json")
    # print("File current_processed_variants.json deleted successfully.")
except FileNotFoundError:
    print("The file current_processed_variants.json does not exist.")
except PermissionError:
    print("You do not have permission to delete current_processed_variants.json file.")

print("CLIENT.clear() ...")
CLIENT.clear()

flag = True
for variant in variants_expanded:
    errors = variant.get("errors", None)
    if errors:
        if flag:
            print("")
            print("*** ERRORS ***")
            flag = False
        for error in errors:
            print(f"{variant['hash']} {error}")

print("Batch finish:", dts())
print("Total time:", int(time.time() - t00), "seconds")

write_config(CONFIG)
exit(0)