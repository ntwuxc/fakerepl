import base64
from PIL import Image
from io import BytesIO
import os

#from IPython.

_TEXT_SAVED_IMAGE = "bash_kernel: saved image data to:"

image_setup_cmd = """
display () {
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    echo "%s $TMPFILE" >&2
}
""" % _TEXT_SAVED_IMAGE

def display_data_for_image(filename):
    image = Image.open(filename)
    os.unlink(filename)
    f = BytesIO()
    image.save(f, "png")

    image_data = base64.b64encode(f.getvalue()).decode('ascii')
    content = {
        'data': {
            'image/png' : image_data
        },
        'metadata': {}
    }
    return content
