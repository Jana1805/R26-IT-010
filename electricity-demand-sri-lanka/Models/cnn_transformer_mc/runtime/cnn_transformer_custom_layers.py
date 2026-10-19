import numpy as np
import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package="LoadForecasting")
class PositionalEncoding(tf.keras.layers.Layer):
    """Fixed sinusoidal positional encoding for temporal order."""

    def __init__(self, max_seq_len, d_model, **kwargs):
        super().__init__(**kwargs)
        self.max_seq_len = int(max_seq_len)
        self.d_model = int(d_model)

        position = np.arange(self.max_seq_len, dtype=np.float32)[:, np.newaxis]
        dimension = np.arange(self.d_model, dtype=np.float32)[np.newaxis, :]
        angle_rates = 1.0 / np.power(
            10000.0, (2 * np.floor(dimension / 2)) / self.d_model
        )
        angles = position * angle_rates

        encoding = np.zeros((self.max_seq_len, self.d_model), dtype=np.float32)
        encoding[:, 0::2] = np.sin(angles[:, 0::2])
        encoding[:, 1::2] = np.cos(angles[:, 1::2])
        self.positional_encoding = tf.constant(encoding[np.newaxis, :, :])

    def call(self, inputs):
        sequence_length = tf.shape(inputs)[1]
        encoding = tf.cast(
            self.positional_encoding[:, :sequence_length, :], inputs.dtype
        )
        return inputs + encoding

    def get_config(self):
        config = super().get_config()
        config.update({
            "max_seq_len": self.max_seq_len,
            "d_model": self.d_model,
        })
        return config


@tf.keras.utils.register_keras_serializable(package="LoadForecasting")
class TransformerBlock(tf.keras.layers.Layer):
    """Transformer encoder with attention and feed-forward residuals."""

    def __init__(
        self, d_model, n_heads, d_ff, dropout_rate,
        layer_norm_eps=1e-6, **kwargs
    ):
        super().__init__(**kwargs)
        self.d_model = int(d_model)
        self.n_heads = int(n_heads)
        self.d_ff = int(d_ff)
        self.dropout_rate = float(dropout_rate)
        self.layer_norm_eps = float(layer_norm_eps)

        self.attention = tf.keras.layers.MultiHeadAttention(
            num_heads=self.n_heads,
            key_dim=self.d_model // self.n_heads,
            dropout=self.dropout_rate,
        )
        self.attention_dropout = tf.keras.layers.Dropout(self.dropout_rate)
        self.attention_norm = tf.keras.layers.LayerNormalization(
            epsilon=self.layer_norm_eps
        )

        self.ffn_dense_1 = tf.keras.layers.Dense(self.d_ff, activation="relu")
        self.ffn_dense_2 = tf.keras.layers.Dense(self.d_model)
        self.ffn_dropout = tf.keras.layers.Dropout(self.dropout_rate)
        self.ffn_norm = tf.keras.layers.LayerNormalization(
            epsilon=self.layer_norm_eps
        )

    def call(self, inputs, training=None):
        attention_output = self.attention(inputs, inputs, training=training)
        attention_output = self.attention_dropout(
            attention_output, training=training
        )
        x = self.attention_norm(inputs + attention_output)

        ffn_output = self.ffn_dense_2(self.ffn_dense_1(x))
        ffn_output = self.ffn_dropout(ffn_output, training=training)
        return self.ffn_norm(x + ffn_output)

    def get_config(self):
        config = super().get_config()
        config.update({
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "d_ff": self.d_ff,
            "dropout_rate": self.dropout_rate,
            "layer_norm_eps": self.layer_norm_eps,
        })
        return config
