# # Convert Model.py

# import tensorflow as tf
# from keras.losses import MeanSquaredError

# # Bypass compile config khi load
# model = tf.keras.models.load_model("model.h5", compile=False)
# model.compile(optimizer='adam', loss=MeanSquaredError())

# converter = tf.lite.TFLiteConverter.from_keras_model(model)
# tflite_model = converter.convert()

# with open("model.tflite", "wb") as f:
#     f.write(tflite_model)



import tensorflow as tf

model = tf.keras.models.load_model("custom_model.h5", compile=False)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS,
    tf.lite.OpsSet.SELECT_TF_OPS,
]
converter._experimental_lower_tensor_list_ops = False
tflite_model = converter.convert()
with open("custom_model.tflite", "wb") as f:
    f.write(tflite_model)

print("✅")
