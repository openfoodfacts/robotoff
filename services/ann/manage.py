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
        from annoy import AnnoyIndex
        from embeddings import EMBEDDING_STORE

        index = None
        offset: int = 0
        keys = []

        for logo_id, embedding in EMBEDDING_STORE.iter_embeddings():
            if index is None:
                output_dim = embedding.shape[-1]
                index = AnnoyIndex(output_dim, "euclidean")

            index.add_item(offset, embedding)
            keys.append(int(logo_id))
            offset += 1

        if index is not None:
            index.build(tree_count)
            index.save(str(output))

            with output.with_suffix(".txt").open("w") as f:
                for key in keys:
                    f.write(str(key) + "\n")

    cli.add_command(generate_index)
    cli()
