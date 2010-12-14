"Create RDKit fingerprints"

# Copyright (c) 2010 Andrew Dalke Scientific, AB (Gothenburg, Sweden)
# See the contents of "__init__.py" for full license details.

from __future__ import absolute_import

import os
import sys
import gzip

import rdkit
from rdkit import Chem
from rdkit.Chem.MACCSkeys import GenMACCSKeys


from . import sdf_reader, decoders, decompressors, error_handlers

# These are the things I consider to be public
__all__ = ["read_structures", "iter_smiles_molecules", "iter_sdf_molecules"]

######## Some shenanigans to get a version field

if hasattr(rdkit, "version"):
    # This will be available in the next release of RDKit
    SOFTWARE = "RDKit/" + rdkit.version()
else:
    # This distribution does not have version().
    # Guess based on the evidence.

    # This was added in Release_Q22009_1
    import rdkit.Chem.AtomPairs.Torsions
    if not hasattr(Chem.AtomPairs.Torsions, "GetHashedTopologicalTorsionFingerprint"):
        SOFTWARE = "RDKit/unknown"
    else:
        # Either Release_Q22009_1 or Release_Q32009_1
        # Q3 removed the DaylightFingerprint function.
        if hasattr(Chem, "DaylightFingerprint"):
            # In 2010 the version numbers were put into lexical order.
            # Keep with the same principle.
            SOFTWARE = "RDKit/2009Q2_1"
        else:
            SOFTWARE = "RDKit/2009Q3_1"

##### Convert from RDKit explicit (dense) fingerprints to byte strings



#########
_allowed_formats = ["sdf", "smi"]
_format_extensions = {
    ".sdf": "sdf",
    ".mol": "sdf",
    ".sd": "sdf",
    ".mdl": "sdf",

    ".smi": "smi",
    ".can": "smi",
    ".smiles": "smi",
    ".ism": "smi",
}
            
def normalize_input(source=None, format=None, decompressor=None):
    if decompressor is not None:
        decompressor = decompressors.get_named_decompressor(decompressor)
        
    if format is not None:
        if decompressor is None:
            decompressor = decompressors.detect_decompressor(format)
        base_format = decompressor.strip_extension(format)
        if base_format not in _allowed_formats:
            msg = "Unknown structure format {format!r}. Supported formats are: {all}".format(
                format=base_format, all=", ".join(_allowed_formats))
            raise TypeError(msg)
        return base_format, decompressor
        
    elif source is not None:
        format_specified = False
        if decompressor is None:
            decompressor = decompressors.detect_decompressor(source)
        base_filename = decompressor.strip_extension(source)
        ext = os.path.splitext(base_filename)[1].lower()
        try:
            return _format_extensions[ext], decompressor
        except KeyError:
            # Unknown extension, assume SMILES
            return "smi", decompressor
    else:
        if decompressor is None:
            decompressor = decompressors.Uncompressed
        return "smi", decompressor


class SmilesFileLocation(object):
    def __init__(self, filename=None):
        self.filenme = filename
        self.lineno = 1
    def where(self):
        s = "at line {self.lineno}"
        if self.filename is not None:
            s += " of {self.filename}"
        return s.format(self=self)
    

# While RDKit has a SMILES file parser, it doesn't handle reading from
# stdin or from compressed files. I wanted to support those as well, so
# ended up not using Chem.SmilesMolSupplier.

def iter_smiles_molecules(infile, source=None, errors="strict"):
    """iter_smiles_molecules(infile) -> (title, Chem.Mol) iterator

    Iterate through each record in the SMILES file, returning the
    2-ple of (title, rdkit.Chem.Mol). Each record is a single line of
    fields, separated by whitespace. The first column is the SMILES
    used to create the molecule. It must be present. The second column
    is the title. If not present, the record number (starting with
    "1") is used as the title.
    """
    if source is None:
        source = getattr(infile, "name", None)
    error_handler = error_handlers.get_parse_error_handler(errors)

    loc = SmilesFileLocation(source)
    for lineno, line in enumerate(infile):
        words = line.split()
        if not words:
            loc.lineno = lineno+1
            error_handler("unexpected blank line", loc)
            continue

        mol = Chem.MolFromSmiles(words[0])
        if mol is None:
            loc.lineno = lineno+1
            error_handler("Cannot parse the SMILES %r" % (words[0],), loc)
            continue
        
        if len(words) == 1:
            yield str(lineno+1), mol
        else:
            yield words[1], mol


def iter_sdf_molecules(infile, filename=None, errors="strict"):
    """iter_sdf_molecules(infile) -> (title, Chem.Mol) iterator

    Iterate through each record in the SD file, returning the 2-ple of
    (title, rdkit.Chem.Mol). The title comes from the "_Name" property
    of the molecule object.
    """
    # If there's no explicit filename, see if 'infile' has one
    if filename is None:
        filename = getattr(infile, "name", None)

    loc = sdf_reader.FileLocation(filename)
    for text in sdf_reader.iter_sdf_records(infile, loc, errors):
        mol = Chem.MolFromMolBlock(text)
        if mol is None:
            # This was not a molecule?
            reader_error("Could not parse molecule block", loc)
        else:
            yield mol.GetProp("_Name"), mol

# This class helps the case when someone is entering structure
# by-hand. (Most likely to occur with SMILES input). They would like
# to see the result as soon as a record is entered. But normal
# interation reader grabs a buffer of input to process, and not a
# line. It's faster that way. The following adapter supports the
# iterator protocol but turns it into simple readlines(). This will be
# slower but since do it only if stdin is a tty, there shouldn't be a
# problem.
## class _IterUsingReadline(object):
##     "Internal class for iterating a line at a time from tty input"
##     def __init__(self, fileobj):
##         self.fileobj = fileobj
##     def __iter__(self):
##         return iter(self.fileobj.readline, "")

## def _open(filename, compressed):
##     "Internal function to open the given filename, which might be compressed"
##     if filename is None:
##         if compressed:
##             return gzip.GzipFile(fileobj=sys.stdin, mode="r")
##         else:
##             # Python's iter reads a block.
##             # When someone types interactively, read only a line.
##             if sys.stdin.isatty():
##                 return _IterUsingReadline(sys.stdin)
##             else:
##                 return sys.stdin

##     if compressed:
##         return gzip.GzipFile(filename, "r")
##     return open(filename, "rU")
    

def read_structures(source, format=None, decompressor=None, errors="strict"):
    """read_structures(source, format, decompressor, on_error) -> (title, rdkit.Chem.Mol) iterator 
    
    Iterate over each record in the source, yielding the structure's
    title and corresponding RDKit.Chem.Mol
    """
    format, decompressor = normalize_input(source, format, decompressor)
    if format == "sdf":
        # I have an old PubChem file Compound_09425001_09450000.sdf .
        #   num. lines = 5,041,475   num. bytes = 159,404,037
        # 
        # Parse times for iter_sdf_records (parsing records in Python)
        #   37.6s (best of 37.6, 38.3, 37.8)
        # Parse times for the RDKit implementation (parsing records in C++)
        #   40.2s (best of 41.7, 41.33, 40.2)
        # 
        # The native RDKit reader is slower than the Python one and does
        # not have (that I can tell) support for compressed files, so
        # I'll go with the Python one. For those interested, here's the
        # RDKit version.
        # 
        #if (not compressed) and (source is not None):
        #    supplier = Chem.SDMolSupplier(source)
        #    def native_sdf_reader():
        #        for mol in supplier:
        #            if mol is None:
        #                print >>sys.stderr, "Missing? after", title
        #            else:
        #                title = mol.GetProp("_Name")
        #                yield title, mol
        #    return native_sdf_reader()

        infile = decompressors.open_and_decompress_universal(source, decompressor)
        return iter_sdf_molecules(infile, source, errors)

    elif format == "smi":
        # I timed the native reader at 31.6 seconds (best of 31.6, 31.7, 31.7)
        # and the Python reader at 30.8 seconds (best of 30.8, 30.9, and 31.0)
        # Yes, the Python reader is faster and using it gives me better consistency
        #
        #if (not compressed) and (source is not None):
        #    supplier = Chem.SmilesMolSupplier(source, delimiter=" \t", titleLine=False)
        #    def native_smiles_reader():
        #        for mol in supplier:
        #            yield mol.GetProp("_Name"), mol
        #    return native_smiles_reader()
        infile = decompressors.open_and_decompress_universal(source, decompressor)
        return iter_smiles_molecules(infile, source, errors)

    else:
        raise TypeError("Unsupported format {format!r}".format(format=format))

########### The topological fingerprinter

# Some constants shared by the fingerprinter and the command-line code.

NUM_BITS = 2048
MIN_PATH = 1
MAX_PATH = 7
BITS_PER_HASH = 4
USE_HS = 1
assert USE_HS == 1, "Don't make this 0 unless you know what you are doing"

# Not supporting the tgtDensity and minSize options.
# This program generates fixed-length fingerprints.

def make_rdk_fingerprinter(num_bits=NUM_BITS, min_path=MIN_PATH, max_path=MAX_PATH,
                           bits_per_hash=BITS_PER_HASH, use_Hs=USE_HS):
    # I've already done checks for this, but I'm assuming that people
    # will use this as part of the public API.
    if not (num_bits > 0): raise TypeError("num_bits must be positive")
    if not (min_path > 0): raise TypeError("min_path must be positive")
    if not (max_path >= min_path):
        raise TypeError("max_path cannot be smaller than min_path")
    if not (bits_per_hash > 0): raise TypeError("bits_per_hash must be positive")

    def rdk_fingerprinter(mol):
        fp = Chem.RDKFingerprint(
            mol, minPath=min_path, maxPath=max_path, fpSize=num_bits,
            nBitsPerHash=bits_per_hash, useHs=use_Hs)
        return decoders.from_binary_lsb(fp.ToBitString())[1]
    return rdk_fingerprinter

# Use this to make the parameters for the topological fingerprints
RDK_TYPE = ("RDKit-Fingerprint/1 minPath={min_path} maxPath={max_path} fpSize={num_bits} "
            "nBitsPerHash={bits_per_hash} useHs={use_Hs}")

format_rdk_type = RDK_TYPE.format

########### The MACCS fingerprinter

def maccs166_fingerprinter(mol):
    fp = GenMACCSKeys(mol)
    # In RDKit the first bit is always bit 1 .. bit 0 is empty (?!?!)
    bitstring_with_167_bits = fp.ToBitString()
    return decoders.from_binary_lsb(bitstring_with_167_bits[1:])[1]

