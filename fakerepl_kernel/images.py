import base64
import imghdr
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
    with open(filename, 'rb') as f:
        image = f.read()
    os.unlink(filename)

    image_type = imghdr.what(None, image)
    if image_type is None:
        raise ValueError("Not a valid image: %s" % image)

    image_data = base64.b64encode(image).decode('ascii')
    content = {
        'data': {
            'image/' + image_type: image_data
        },
        'metadata': {}
    }
    return content
