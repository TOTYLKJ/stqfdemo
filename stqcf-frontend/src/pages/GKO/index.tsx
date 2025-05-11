import React, { useState, useEffect, useRef } from 'react';
import { Button, Card, message, Spin, Space, Typography } from 'antd';
import styles from './styles.module.css';
import { buildTreeIndex, distributeTrajectoryPoints } from '@api/gko';

const { Title } = Typography;

// Octree node interface
interface OctreeNode {
  id: string;
  level: number;
  children: OctreeNode[];
  expanded: boolean;
}

const GKOPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [processingOctree, setProcessingOctree] = useState<boolean>(false);
  const [processingTrajectory, setProcessingTrajectory] = useState<boolean>(false);
  const [rootNode, setRootNode] = useState<OctreeNode>({
    id: 'root',
    level: 0,
    children: [],
    expanded: false,
  });

  // Initialize octree
  useEffect(() => {
    initializeOctree();
  }, []);

  // Initialize octree data
  const initializeOctree = () => {
    const root: OctreeNode = {
      id: 'root',
      level: 0,
      children: [],
      expanded: false,
    };
    setRootNode(root);
  };

  // Handle node click event
  const handleNodeClick = (node: OctreeNode) => {
    if (node.level >= 2) return; // Maximum 3 levels

    // If already expanded, collapse it
    if (node.expanded) {
      const updatedNode = { ...node, expanded: false };
      updateNodeInTree(updatedNode);
      return;
    }

    // If not expanded and has no children, generate children
    if (!node.expanded && node.children.length === 0) {
      const children: OctreeNode[] = [];
      for (let i = 0; i < 8; i++) {
        children.push({
          id: `${node.id}-${i}`,
          level: node.level + 1,
          children: [],
          expanded: false,
        });
      }

      const updatedNode = { ...node, children, expanded: true };
      updateNodeInTree(updatedNode);
    } else {
      // If not expanded but has children, expand it
      const updatedNode = { ...node, expanded: true };
      updateNodeInTree(updatedNode);
    }
  };

  // Update node in the tree
  const updateNodeInTree = (updatedNode: OctreeNode) => {
    if (updatedNode.id === 'root') {
      setRootNode(updatedNode);
      return;
    }

    const updateNode = (node: OctreeNode): OctreeNode => {
      if (node.id === updatedNode.id) {
        return updatedNode;
      }

      if (node.children.length > 0) {
        return {
          ...node,
          children: node.children.map((child) => updateNode(child)),
        };
      }

      return node;
    };

    setRootNode(updateNode(rootNode));
  };

  // Get node display name
  const getNodeDisplayName = (node: OctreeNode): string => {
    // First level: root -> Root
    if (node.level === 0) {
      return 'Root';
    }

    // Second level: root-0, root-1, ... -> Node-0, Node-1, ...
    if (node.level === 1) {
      // Extract number part from ID
      const index = node.id.split('-')[1];
      return `Node-${index}`;
    }

    // Third level: root-0-0, root-0-1, ... -> Leaf-00, Leaf-01, ...
    if (node.level === 2) {
      // Extract parent and current node indexes from ID
      const parts = node.id.split('-');
      const parentIndex = parts[1];
      const childIndex = parts[2];
      return `Leaf-${parentIndex}${childIndex}`;
    }

    return node.id; // Default to original ID
  };

  // Build tree index
  const handleBuildTreeIndex = async () => {
    try {
      setProcessingOctree(true);
      message.loading('Building octree data migration...', 0);

      const response = await buildTreeIndex();
      console.log('Build tree index response:', response);

      if (response.success) {
        message.success('Octree data migration successful!');
      } else {
        message.error(`Octree data migration failed: ${response.message}`);
      }
    } catch (error) {
      console.error('Error during octree data migration:', error);
      message.error('Octree data migration failed, please check console for details');
    } finally {
      setProcessingOctree(false);
      message.destroy();
    }
  };

  // Distribute trajectory points
  const handleDistributeTrajectoryPoints = async () => {
    try {
      setProcessingTrajectory(true);
      message.loading('Distributing trajectory points...', 0);

      const response = await distributeTrajectoryPoints();

      if (response.success) {
        message.success('Trajectory points distribution successful!');
      } else {
        message.error(`Trajectory points distribution failed: ${response.message}`);
      }
    } catch (error) {
      console.error('Error distributing trajectory points:', error);
      message.error('Trajectory points distribution failed, please check console for details');
    } finally {
      setProcessingTrajectory(false);
      message.destroy();
    }
  };

  // Render octree node
  const renderNode = (node: OctreeNode) => {
    // Adjust node size calculation method, provide larger size for leaf nodes
    let nodeSize = 100 - node.level * 25; // Reduce level's impact on size

    // Specially increase size for leaf nodes
    if (node.level === 2) {
      nodeSize = 65; // Increase leaf node size to 65px
    }

    const displayName = getNodeDisplayName(node); // Get node display name

    return (
      <div
        key={node.id}
        className={styles.nodeContainer}
        style={{
          margin: node.level === 2 ? '15px' : '10px', // Increase margin for leaf nodes
        }}
      >
        <div
          className={`${styles.node} ${node.level === 2 ? styles.leafNode : ''}`}
          style={{
            width: `${nodeSize}px`,
            height: `${nodeSize}px`,
          }}
          onClick={() => handleNodeClick(node)}
          data-level={node.level}
        >
          <span className={styles.nodeId}>{displayName}</span>
        </div>

        {node.expanded && node.children.length > 0 && (
          <div
            className={styles.childrenContainer}
            style={{
              maxWidth: node.level === 1 ? '1000px' : '800px', // Increase max width for second level children container
            }}
          >
            {node.children.map((child) => renderNode(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={styles.container}>
      <Title level={2}>GKO Octree Management</Title>

      <Card className={styles.treeCard}>
        <div className={styles.treeContainer}>{renderNode(rootNode)}</div>
      </Card>

      <div className={styles.buttonContainer}>
        <Space size='large'>
          <Button
            type='primary'
            size='large'
            loading={processingOctree}
            onClick={handleBuildTreeIndex}
            disabled={processingTrajectory}
          >
            Build Octree
          </Button>

          <Button
            type='primary'
            size='large'
            loading={processingTrajectory}
            onClick={handleDistributeTrajectoryPoints}
            disabled={processingOctree}
          >
            Distribute Trajectory Points
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default GKOPage;
