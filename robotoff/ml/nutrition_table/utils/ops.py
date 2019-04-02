import tensorflow as tf
import numpy as np
import PIL
from PIL import Image


def reframe_box_masks_to_image_masks(box_masks, boxes, image_height,
                                     image_width):
    """Transforms the box masks back to full image masks.
    Embeds masks in bounding boxes of larger masks whose shapes correspond to
    image shape.
    Args:
      box_masks: A tf.float32 tensor of size [num_masks, mask_height, mask_width].
      boxes: A tf.float32 tensor of size [num_masks, 4] containing the box
             corners. Row i contains [ymin, xmin, ymax, xmax] of the box
             corresponding to mask i. Note that the box corners are in
             normalized coordinates.
      image_height: Image height. The output mask will have the same height as
                    the image height.
      image_width: Image width. The output mask will have the same width as the
                   image width.
    Returns:
      A tf.float32 tensor of size [num_masks, image_height, image_width].
    """

    # TODO(rathodv): Make this a public function.
    def reframe_box_masks_to_image_masks_default():
        """The default function when there are more than 0 box masks."""

        def transform_boxes_relative_to_boxes(boxes, reference_boxes):
            boxes = tf.reshape(boxes, [-1, 2, 2])
            min_corner = tf.expand_dims(reference_boxes[:, 0:2], 1)
            max_corner = tf.expand_dims(reference_boxes[:, 2:4], 1)
            transformed_boxes = (boxes - min_corner) / (max_corner - min_corner)
            return tf.reshape(transformed_boxes, [-1, 4])

        box_masks_expanded = tf.expand_dims(box_masks, axis=3)
        num_boxes = tf.shape(box_masks_expanded)[0]
        unit_boxes = tf.concat(
            [tf.zeros([num_boxes, 2]), tf.ones([num_boxes, 2])], axis=1)
        reverse_boxes = transform_boxes_relative_to_boxes(unit_boxes, boxes)
        return tf.image.crop_and_resize(
            image=box_masks_expanded,
            boxes=reverse_boxes,
            box_ind=tf.range(num_boxes),
            crop_size=[image_height, image_width],
            extrapolation_value=0.0)

    image_masks = tf.cond(
        tf.shape(box_masks)[0] > 0,
        reframe_box_masks_to_image_masks_default,
        lambda: tf.zeros([0, image_height, image_width, 1], dtype=tf.float32))
    return tf.squeeze(image_masks, axis=3)


def convert_image_to_array(image: PIL.Image.Image) -> np.array:
    if image.mode != 'RGB':
        image = image.convert('RGB')

    (im_width, im_height) = image.size

    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)
