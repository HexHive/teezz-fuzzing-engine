.PHONY: clean executor

executor:
	ndk-build

executor-optee:
	$(MAKE) -C jni/

clean:
	$(RM) -rf libs/ obj/

