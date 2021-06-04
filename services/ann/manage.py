if __name__ == "__main__":
    import pathlib

    import click

    @click.group()
    def cli():
        pass

    @click.command()
    @click.argument("output", type=pathlib.Path)
    @click.option("--tree-count", type=int, default=100)
    def generate_index(output: pathlib.Path, tree_count: int):
        import shutil
        import tempfile

        import settings
        import tqdm
        from annoy import AnnoyIndex
        from embeddings import EmbeddingStore
        from utils import get_logger

        logger = get_logger()

        with tempfile.TemporaryDirectory() as tmp_dir:
            embedding_path = pathlib.Path(tmp_dir) / "embeddings.hdf5"
            logger.info(f"Copying embedding file to {embedding_path}...")
            shutil.copy(str(settings.EMBEDDINGS_HDF5_PATH), str(embedding_path))

            logger.info(f"Loading {embedding_path}...")
            embedding_store = EmbeddingStore(embedding_path)

            index = None
            offset: int = 0
            keys = []

            logger.info("Adding embeddings to index...")
            for logo_id, embedding in tqdm.tqdm(embedding_store.iter_embeddings()):
                if index is None:
                    output_dim = embedding.shape[-1]
                    index = AnnoyIndex(output_dim, "euclidean")

                index.add_item(offset, embedding)
                keys.append(int(logo_id))
                offset += 1

            logger.info("Building index...")
            if index is not None:
                index.build(tree_count)
                index.save(str(output))

                logger.info("Index built.")
                logger.info("Saving keys...")

                with output.with_suffix(".txt").open("w") as f:
                    for key in keys:
                        f.write(str(key) + "\n")

                logger.info("Keys saved.")

    cli.add_command(generate_index)
    cli()
