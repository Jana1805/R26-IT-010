"""Custom Keras layers required to deserialize the Transformer / CNN-Transformer
models. Must be imported (for its registration side-effects) before
tf.keras.models.load_model() is called on either model.
"""

import keras
import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import Dense, Dropout, LayerNormalization, MultiHeadAttention


@keras.saving.register_keras_serializable(package="LoadForecasting")
class PositionalEncoding(tf.keras.layers.Layer):
    """Sinusoidal positional encoding (Vaswani et al., 2017)."""

    def __init__(self, max_seq_len, d_model, **kwargs):
        super().__init__(**kwargs)
        self.max_seq_len = max_seq_len
        self.d_model = d_model

        pe = np.zeros((max_seq_len, d_model))
        position = np.arange(0, max_seq_len, dtype=np.float32)[:, np.newaxis]
        div_term = np.exp(
            np.arange(0, d_model, 2, dtype=np.float32) * -(np.log(10000.0) / d_model)
        )
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)

        compute_dtype = tf.keras.mixed_precision.global_policy().compute_dtype
        self.pe = tf.constant(pe[np.newaxis, :, :], dtype=compute_dtype)

    def call(self, x):
        return x + tf.cast(self.pe[:, :tf.shape(x)[1], :], x.dtype)

    def get_config(self):
        config = super().get_config()
        config.update({"max_seq_len": self.max_seq_len, "d_model": self.d_model})
        return config


@keras.saving.register_keras_serializable(package="LoadForecasting")
class TransformerBlock(tf.keras.layers.Layer):
    """Multi-Head Self-Attention + FeedForward, each with residual + LayerNorm."""

    def __init__(self, d_model, n_heads, d_ff, dropout_rate=None, dropout=None, layer_norm_eps=1e-6, **kwargs):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_ff = d_ff
        self.dropout = float(dropout_rate if dropout_rate is not None else dropout)
        self.layer_norm_eps = float(layer_norm_eps)

        self.attention = MultiHeadAttention(num_heads=n_heads, key_dim=d_model // n_heads, dropout=self.dropout)
        self.attention_norm = LayerNormalization(epsilon=self.layer_norm_eps)
        self.attention_dropout = Dropout(self.dropout)
        self.ffn_dense_1 = Dense(d_ff, activation="relu")
        self.ffn_dense_2 = Dense(d_model)
        self.ffn_norm = LayerNormalization(epsilon=self.layer_norm_eps)
        self.ffn_dropout = Dropout(self.dropout)

    def call(self, x, training=False):
        attn_out = self.attention(x, x, training=training)
        attn_out = self.attention_dropout(attn_out, training=training)
        x = self.attention_norm(x + attn_out)
        ff_out = self.ffn_dense_2(self.ffn_dense_1(x))
        ff_out = self.ffn_dropout(ff_out, training=training)
        x = self.ffn_norm(x + ff_out)

        return x

    def get_config(self):
        config = super().get_config()
        config.update({
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "d_ff": self.d_ff,
            "dropout_rate": self.dropout,
            "layer_norm_eps": self.layer_norm_eps,
        })
        return config
